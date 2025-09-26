#!/usr/bin/env python3
"""
Certificate Generator - Andrew Spangler
Generates root CA, domain, and wildcard certificates for development use.
"""

import os
import datetime
import logging
from pathlib import Path
from typing import List, Optional

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

def check_certificates_exist(domain: str, certs_dir: str = "/certs", logger=None) -> bool:
    certs_path = Path(certs_dir)
    files = (
        str(certs_path / "rootCA-key.pem"),
        str(certs_path / "rootCA.pem"),
        str(certs_path / f"{domain}-key.pem"),
        str(certs_path / f"{domain}.pem"),
        str(certs_path / f"_wildcard.{domain}-key.pem"),
        str(certs_path / f"_wildcard.{domain}.pem")
    )
    for f in files:
        if not os.path.exists(f):
            print(f, "missing")
            return False
    return True

def generate_certificates(domain: str, certs_dir: str = "./certs", logger=None) -> dict:
    """
    Generate root CA, domain certificate, and wildcard certificate for a given domain.
    
    Args:
        domain: The domain name (e.g., 'example.com')
        certs_dir: Directory to store certificates (default: './certs')
    
    Returns:
        dict: Dictionary containing paths to generated certificate files
    """
    certs_path = Path(certs_dir)
    certs_path.mkdir(exist_ok=True)
    
    root_ca_key_path = certs_path / "rootCA-key.pem"
    root_ca_cert_path = certs_path / "rootCA.pem"
    
    if not (root_ca_key_path.exists() and root_ca_cert_path.exists()):
        if logger:
            logger.info("Generating root CA...")
        root_ca_key, root_ca_cert = _generate_root_ca()
        _save_key_and_cert(root_ca_key, root_ca_cert, root_ca_key_path, root_ca_cert_path)
    else:
        if logger:
            logger.info("Root CA already exists, loading...")
        root_ca_key, root_ca_cert = _load_root_ca(root_ca_key_path, root_ca_cert_path)
    
    if logger:
        logger.info(f"Generating certificate for {domain}...")
    domain_key, domain_cert = _generate_certificate(
        common_name=domain,
        dns_names=[domain],
        ca_key=root_ca_key,
        ca_cert=root_ca_cert
    )
    
    domain_key_path = certs_path / f"{domain}-key.pem"
    domain_cert_path = certs_path / f"{domain}.pem"
    _save_key_and_cert(domain_key, domain_cert, domain_key_path, domain_cert_path)
    
    if logger:
        logger.info(f"Generating wildcard certificate for *.{domain}...")
    wildcard_key, wildcard_cert = _generate_certificate(
        common_name=f"*.{domain}",
        dns_names=[f"*.{domain}", domain],
        ca_key=root_ca_key,
        ca_cert=root_ca_cert
    )
    
    wildcard_key_path = certs_path / f"_wildcard.{domain}-key.pem"
    wildcard_cert_path = certs_path / f"_wildcard.{domain}.pem"
    _save_key_and_cert(wildcard_key, wildcard_cert, wildcard_key_path, wildcard_cert_path)
    
    if logger:
        logger.info("Done!")
    
    created_files = {
        'root_ca_key': str(root_ca_key_path),
        'root_ca_cert': str(root_ca_cert_path),
        'domain_key': str(domain_key_path),
        'domain_cert': str(domain_cert_path),
        'wildcard_key': str(wildcard_key_path),
        'wildcard_cert': str(wildcard_cert_path)
    }
    
    if logger:
        logger.info("Created files:")
        for file_type, file_path in created_files.items():
            logger.info(f" - {file_path}")
    
    return created_files


def _generate_private_key() -> rsa.RSAPrivateKey:
    """Generate a 2048-bit RSA private key."""
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


def _generate_root_ca() -> tuple:
    """Generate root CA key and certificate."""
    key = _generate_private_key()
    
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "LoStack Development CA"),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=3650)  # 10 years
    ).add_extension(
        x509.SubjectAlternativeName([]),
        critical=False,
    ).add_extension(
        x509.BasicConstraints(ca=True, path_length=None),
        critical=True,
    ).add_extension(
        x509.KeyUsage(
            key_cert_sign=True,
            crl_sign=True,
            key_encipherment=False,
            data_encipherment=False,
            key_agreement=False,
            content_commitment=False,
            digital_signature=False,
            encipher_only=False,
            decipher_only=False
        ),
        critical=True,
    ).sign(key, hashes.SHA256())
    
    return key, cert


def _generate_certificate(common_name: str, dns_names: List[str], ca_key, ca_cert) -> tuple:
    """Generate a certificate signed by the given CA."""
    key = _generate_private_key()
    
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])
    
    san_list = [x509.DNSName(dns_name) for dns_name in dns_names]
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        ca_cert.subject
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365)  # 1 year
    ).add_extension(
        x509.SubjectAlternativeName(san_list),
        critical=False,
    ).add_extension(
        x509.BasicConstraints(ca=False, path_length=None),
        critical=True,
    ).add_extension(
        x509.KeyUsage(
            key_cert_sign=False,
            crl_sign=False,
            key_encipherment=True,
            data_encipherment=False,
            key_agreement=False,
            content_commitment=False,
            digital_signature=True,
            encipher_only=False,
            decipher_only=False
        ),
        critical=True,
    ).add_extension(
        x509.ExtendedKeyUsage([
            ExtendedKeyUsageOID.SERVER_AUTH,
            ExtendedKeyUsageOID.CLIENT_AUTH,
        ]),
        critical=True,
    ).sign(ca_key, hashes.SHA256())
    
    return key, cert


def _save_key_and_cert(key, cert, key_path: Path, cert_path: Path):
    """Save private key and certificate to files."""
    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))


def _load_root_ca(key_path: Path, cert_path: Path) -> tuple:
    """Load existing root CA key and certificate."""
    with open(key_path, "rb") as f:
        key = serialization.load_pem_private_key(f.read(), password=None)
    
    with open(cert_path, "rb") as f:
        cert = x509.load_pem_x509_certificate(f.read())
    
    return key, cert



if __name__ == "__main__":
    main()