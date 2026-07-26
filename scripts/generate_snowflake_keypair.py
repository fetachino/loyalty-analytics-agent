"""Generate an encrypted RSA key pair for Snowflake authentication."""

import argparse
import getpass
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate(output_directory: Path) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    private_path = output_directory / "snowflake_rsa_key.p8"
    public_path = output_directory / "snowflake_rsa_key.pub"
    if private_path.exists() or public_path.exists():
        raise FileExistsError("Refusing to overwrite an existing Snowflake key pair")

    passphrase = getpass.getpass("Private-key passphrase (minimum 16 characters): ")
    confirmation = getpass.getpass("Confirm passphrase: ")
    if passphrase != confirmation:
        raise ValueError("Passphrases do not match")
    if len(passphrase) < 16:
        raise ValueError("Passphrase must contain at least 16 characters")

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(passphrase.encode()),
        )
    )
    public_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    os.chmod(private_path, 0o600)
    return private_path, public_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-directory",
        type=Path,
        required=True,
        help="Directory outside the repository where the key pair will be written",
    )
    arguments = parser.parse_args()
    private_path, public_path = generate(arguments.output_directory)
    print(f"Encrypted private key: {private_path}")
    print(f"Public key: {public_path}")


if __name__ == "__main__":
    main()
