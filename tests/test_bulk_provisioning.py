"""Tests for Bulk User Provisioning and CSV row-level validation."""
import io


def test_bulk_provisioning_batch_creation(client, auth_headers, sample_devices):
    """Test creating a multi-PC bulk user provisioning batch."""
    payload = {
        "batch_name": "CS101-Morning-Lab",
        "items": [
            {
                "hostname": "LAB-PC-01",
                "username": "student101",
                "initial_password": "InitialPass101#",
                "role": "Student",
                "force_password_change": True
            },
            {
                "hostname": "LAB-PC-02",
                "username": "student102",
                "initial_password": "InitialPass102#",
                "role": "Student",
                "force_password_change": True
            },
            {
                "hostname": "LAB-PC-03",
                "username": "labassistant1",
                "initial_password": "InitialPassAsst#",
                "role": "Lab Assistant",
                "force_password_change": False
            }
        ]
    }

    res = client.post("/api/v1/provisioning/bulk", headers=auth_headers, json=payload)
    assert res.status_code == 201
    batch = res.json()
    assert batch["name"] == "CS101-Morning-Lab"
    assert batch["total_tasks"] == 3
    assert len(batch["tasks"]) == 3
    for t in batch["tasks"]:
        assert t["status"] == "QUEUED"
        assert t["operation"] == "CREATE_USER"


def test_csv_validation_success(client, auth_headers, sample_devices):
    """Test CSV validation with clean, valid input rows."""
    csv_data = (
        "hostname,username,initial_password,role,force_password_change\n"
        "LAB-PC-01,student101,SecretPass101#,Student,true\n"
        "LAB-PC-02,student102,SecretPass102#,Student,true\n"
        "LAB-PC-03,labassistant1,SecretPass103#,Lab Assistant,false\n"
    )

    file_obj = io.BytesIO(csv_data.encode("utf-8"))
    res = client.post(
        "/api/v1/provisioning/validate-csv",
        headers=auth_headers,
        files={"file": ("users.csv", file_obj, "text/csv")}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert data["total_rows"] == 3
    assert data["valid_rows"] == 3
    assert data["invalid_rows"] == 0
    for r in data["rows"]:
        assert r["is_valid"] is True
        assert len(r["errors"]) == 0
        assert r["initial_password"] == "[MASKED]"  # Plaintext masked in response


def test_csv_validation_row_level_diagnostics(client, auth_headers, sample_devices):
    """Test CSV validation catches row-level errors: unknown host, bad username, short password, bad role."""
    csv_data = (
        "hostname,username,initial_password,role,force_password_change\n"
        "UNKNOWN-PC-99,student201,ValidPass201#,Student,true\n"       # Bad host
        "LAB-PC-01,Student202,ValidPass202#,Student,true\n"           # Uppercase username
        "LAB-PC-02,student203,123,Student,true\n"                     # Short password (<6 chars)
        "LAB-PC-03,student204,ValidPass204#,NonExistentRole,true\n"   # Bad role
        "LAB-PC-01,root,ValidPass205#,Student,true\n"                 # Protected username
    )

    file_obj = io.BytesIO(csv_data.encode("utf-8"))
    res = client.post(
        "/api/v1/provisioning/validate-csv",
        headers=auth_headers,
        files={"file": ("users_with_errors.csv", file_obj, "text/csv")}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is False
    assert data["total_rows"] == 5
    assert data["invalid_rows"] == 5

    rows = data["rows"]
    assert any("not registered" in err.lower() for err in rows[0]["errors"])
    assert any("invalid username" in err.lower() for err in rows[1]["errors"])
    assert any("at least 6 characters" in err.lower() for err in rows[2]["errors"])
    assert any("does not exist" in err.lower() for err in rows[3]["errors"])
    assert any("protected system account" in err.lower() for err in rows[4]["errors"])
