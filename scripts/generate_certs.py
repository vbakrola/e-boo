"""Generate LAN TLS Certificate Authority (CA) and Server Certificates with SAN for LAN IPs."""
import os
import sys
import socket
import argparse
from datetime import datetime, timedelta, timezone
import ipaddress

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# Add workspace to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.system_info import get_lan_ip


def generate_ca(output_dir: str):
    """Generate Root CA private key and self-signed certificate."""
    os.makedirs(output_dir, exist_ok=True)
    ca_key_path = os.path.join(output_dir, "ca.key")
    ca_crt_path = os.path.join(output_dir, "ca.crt")

    # Generate CA RSA Key (4096 bit)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    with open(ca_key_path, "wb") as f:
        f.write(ca_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Self-sign CA Certificate (valid for 10 years)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Ubuntu Lab LAN Authority"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Ubuntu Lab Local Root CA"),
    ])

    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=False,
                key_cert_sign=True,
                crl_sign=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True
        )
        .sign(ca_key, hashes.SHA256())
    )

    with open(ca_crt_path, "wb") as f:
        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

    print(f"Root CA generated: {ca_crt_path}")
    return ca_key, ca_cert


def generate_server_cert(output_dir: str, ca_key, ca_cert, lan_ips: list[str], hostnames: list[str]):
    """Generate Server certificate signed by Root CA with Subject Alternative Names."""
    server_key_path = os.path.join(output_dir, "server.key")
    server_crt_path = os.path.join(output_dir, "server.crt")

    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with open(server_key_path, "wb") as f:
        f.write(server_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Build SAN entries
    san_list = []
    for host in hostnames:
        san_list.append(x509.DNSName(host))
    for ip_str in lan_ips:
        try:
            san_list.append(x509.IPAddress(ipaddress.ip_address(ip_str)))
        except ValueError:
            pass

    primary_common_name = hostnames[0] if hostnames else "ubuntu-lab-server"
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Ubuntu Lab Manager"),
        x509.NameAttribute(NameOID.COMMON_NAME, primary_common_name),
    ])

    server_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=825))  # ~2 years standard
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName(san_list), critical=False)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_cert_sign=False,
                crl_sign=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True
        )
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False
        )
        .sign(ca_key, hashes.SHA256())
    )

    with open(server_crt_path, "wb") as f:
        f.write(server_cert.public_bytes(serialization.Encoding.PEM))

    print(f"Server certificate generated: {server_crt_path}")
    print(f"Configured SAN IPs: {lan_ips}")
    print(f"Configured SAN Hosts: {hostnames}")


def main():
    parser = argparse.ArgumentParser(description="Generate LAN TLS Certificates for Ubuntu Lab Manager")
    parser.add_argument("--out", default="./certs", help="Output directory for certificates")
    parser.add_argument("--ip", action="append", help="Extra LAN IP to include in Subject Alternative Names")
    parser.add_argument("--hostname", action="append", help="Extra DNS hostname to include in SAN")
    args = parser.parse_args()

    out_dir = os.path.abspath(args.out)
    detected_ip = get_lan_ip()
    local_hostname = socket.gethostname()

    ips = list(set(["127.0.0.1", detected_ip] + (args.ip or [])))
    hosts = list(set(["localhost", local_hostname, "ubuntu-lab-manager.local"] + (args.hostname or [])))

    print(f"Generating TLS certificates in '{out_dir}'...")
    ca_key, ca_cert = generate_ca(out_dir)
    generate_server_cert(out_dir, ca_key, ca_cert, ips, hosts)
    print("\nTLS Certificate Generation Completed!")
    print(f"1. To trust on Ubuntu client PCs:")
    print(f"   sudo cp {os.path.join(out_dir, 'ca.crt')} /usr/local/share/ca-certificates/ubuntu-lab-ca.crt")
    print(f"   sudo update-ca-certificates")


if __name__ == "__main__":
    main()
