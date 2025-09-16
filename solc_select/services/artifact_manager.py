"""
Artifact management service for solc-select.

This module handles downloading, verification, installation, and management
of Solidity compiler artifacts.
"""

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from io import BufferedRandom
from pathlib import Path
from typing import List
from zipfile import ZipFile

import requests
from Crypto.Hash import keccak

from ..constants import ARTIFACTS_DIR
from ..exceptions import ChecksumMismatchError, SolcSelectError
from ..models import Platform, SolcArtifact, SolcVersion
from ..repositories import CompositeRepository


class ArtifactManager:
    """Service for managing Solidity compiler artifacts."""

    def __init__(
        self, repository: CompositeRepository, platform: Platform, session: requests.Session
    ):
        self.repository = repository
        self.platform = platform
        self.session = session

    def get_installed_versions(self) -> List[SolcVersion]:
        """Get list of installed versions.

        Returns:
            List of installed SolcVersion objects
        """
        if not ARTIFACTS_DIR.exists():
            return []

        installed = []
        for item in ARTIFACTS_DIR.iterdir():
            if item.is_dir() and item.name.startswith("solc-"):
                version_str = item.name.replace("solc-", "")
                try:
                    version = SolcVersion.parse(version_str)
                    # Verify the binary exists
                    binary_path = item / f"solc-{version_str}"
                    if binary_path.exists():
                        installed.append(version)
                except ValueError:
                    # Skip invalid version directories
                    continue

        installed.sort()
        return installed

    def is_installed(self, version: SolcVersion) -> bool:
        """Check if a version is installed.

        Args:
            version: Version to check

        Returns:
            True if installed, False otherwise
        """
        artifact_dir = self.get_artifact_directory(version)
        binary_path = artifact_dir / f"solc-{version}"
        return binary_path.exists()

    def get_artifact_directory(self, version: SolcVersion) -> Path:
        """Get the directory where a version's artifacts are stored.

        Args:
            version: Version to get directory for

        Returns:
            Path to the artifact directory
        """
        return ARTIFACTS_DIR / f"solc-{version}"

    def get_binary_path(self, version: SolcVersion) -> Path:
        """Get the path to a version's binary.

        Args:
            version: Version to get binary path for

        Returns:
            Path to the binary
        """
        artifact_dir = self.get_artifact_directory(version)
        return artifact_dir / f"solc-{version}"

    def create_artifact_metadata(self, version: SolcVersion) -> SolcArtifact:
        """Create artifact metadata for a version.

        Args:
            version: Version to create metadata for

        Returns:
            SolcArtifact with download information

        Raises:
            ValueError: If version is not available
        """
        # Get the appropriate repository for this version
        repo = self.repository.get_repository_for_version(version)

        # Get available versions to find the artifact filename
        available = repo.get_available_versions()
        version_str = str(version)

        if version_str not in available:
            raise ValueError(f"Version {version} is not available")

        artifact_filename = available[version_str]
        download_url = repo.get_download_url(version, artifact_filename)
        sha256_hash, keccak256_hash = repo.get_checksums(version)

        binary_path = self.get_binary_path(version)

        return SolcArtifact(
            version=version,
            platform=self.platform,
            download_url=download_url,
            checksum_sha256=sha256_hash,
            checksum_keccak256=keccak256_hash,
            file_path=binary_path,
        )

    def verify_checksum(self, artifact: SolcArtifact, file_handle: BufferedRandom) -> None:
        """Verify the checksums of a downloaded artifact.

        Args:
            artifact: Artifact metadata with expected checksums
            file_handle: Open file handle to verify

        Raises:
            ChecksumMismatchError: If checksums don't match
        """
        sha256_factory = hashlib.sha256()
        keccak_factory = keccak.new(digest_bits=256)

        # Calculate checksums
        file_handle.seek(0)
        for chunk in iter(lambda: file_handle.read(1024000), b""):  # 1MB chunks
            sha256_factory.update(chunk)
            keccak_factory.update(chunk)

        local_sha256 = sha256_factory.hexdigest()
        local_keccak256 = keccak_factory.hexdigest()

        # Verify SHA256
        if artifact.checksum_sha256 != local_sha256:
            raise ChecksumMismatchError(artifact.checksum_sha256, local_sha256, "SHA256")

        # Verify Keccak256 if available
        if artifact.checksum_keccak256 and artifact.checksum_keccak256 != local_keccak256:
            raise ChecksumMismatchError(artifact.checksum_keccak256, local_keccak256, "Keccak256")

    def download_and_install(self, version: SolcVersion, silent: bool = False) -> bool:
        """Download and install a Solidity compiler version.

        Args:
            version: Version to install
            silent: Whether to suppress output messages

        Returns:
            True if successful, False otherwise

        Raises:
            InstallationError: If installation fails
            ChecksumMismatchError: If checksum verification fails
        """
        if self.is_installed(version) and not silent:
            print(f"Version '{version}' is already installed, skipping...")
            return True

        if not silent:
            print(f"Installing solc '{version}'...")

        try:
            artifact = self.create_artifact_metadata(version)
        except ValueError as e:
            if not silent:
                print(f"Error: {e}")
            return False

        # Create artifact directory
        artifact_dir = self.get_artifact_directory(version)
        artifact_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Download the file
            response = self.session.get(artifact.download_url, stream=True)
            response.raise_for_status()

            # Write and verify the file
            with open(artifact.file_path, "w+b", opener=partial(os.open, mode=0o664)) as f:
                try:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:  # Filter out keep-alive chunks
                            f.write(chunk)
                except KeyboardInterrupt:
                    # Clean up partially downloaded file on interrupt
                    if artifact.file_path.exists():
                        artifact.file_path.unlink(missing_ok=True)
                    raise

                # Verify checksums
                self.verify_checksum(artifact, f)

            # Handle ZIP archives (older Windows versions)
            if artifact.is_zip_archive:
                self._extract_zip_archive(artifact)
            else:
                # Make binary executable
                artifact.file_path.chmod(0o775)

            if not silent:
                print(f"Version '{version}' installed.")

            return True

        except Exception as e:
            # Clean up on failure
            if artifact.file_path.exists():
                artifact.file_path.unlink()

            if isinstance(e, ChecksumMismatchError):
                raise e
            else:
                if not silent:
                    print(f"Error installing {version}: {e}")
                return False

    def _extract_zip_archive(self, artifact: SolcArtifact) -> None:
        """Extract a ZIP archive and rename the binary.

        Args:
            artifact: Artifact metadata for the ZIP file
        """
        artifact_dir = artifact.file_path.parent

        with ZipFile(artifact.file_path, "r") as zip_ref:
            zip_ref.extractall(path=artifact_dir)

        # Remove the ZIP file
        artifact.file_path.unlink()

        # Rename the extracted binary
        extracted_binary = artifact_dir / artifact.get_binary_name_in_zip()
        extracted_binary.rename(artifact.file_path)

        # Make executable
        artifact.file_path.chmod(0o775)

    def install_versions(self, versions: List[SolcVersion], silent: bool = False) -> bool:
        """Install multiple versions concurrently.

        Args:
            versions: List of versions to install
            silent: Whether to suppress output messages

        Returns:
            True if all installations succeeded, False otherwise
        """
        if not versions:
            return True

        # For single version, use sequential approach
        if len(versions) == 1:
            try:
                return self.download_and_install(versions[0], silent)
            except SolcSelectError as e:
                if not silent:
                    print(f"Error: {e}")
                return False

        # For multiple versions, use parallel approach
        if not silent:
            print(f"Installing {len(versions)} versions concurrently...")

        success_count = 0
        total_count = len(versions)

        # Use ThreadPoolExecutor with max 5 concurrent downloads
        executor = ThreadPoolExecutor(max_workers=5)
        future_to_version = {}

        try:
            # Submit all download jobs
            future_to_version = {
                executor.submit(self.download_and_install, version, True): version
                for version in versions
            }

            # Process completed downloads
            for future in as_completed(future_to_version):
                version = future_to_version[future]
                try:
                    result = future.result()
                    if result:
                        success_count += 1
                        if not silent:
                            print(
                                f"[OK] Version '{version}' installed ({success_count}/{total_count})"
                            )
                    elif not silent:
                        print(
                            f"[FAIL] Version '{version}' failed to install ({success_count}/{total_count})"
                        )
                except SolcSelectError as e:
                    if not silent:
                        print(
                            f"[FAIL] Version '{version}' failed: {e} ({success_count}/{total_count})"
                        )

        except KeyboardInterrupt:
            if not silent:
                print(f"\nCancelling installation... ({success_count}/{total_count} completed)")

            # Cancel all pending futures
            for future in future_to_version:
                future.cancel()

            # Shutdown executor immediately without waiting for running tasks
            executor.shutdown(wait=False)
            raise

        finally:
            # Clean shutdown for normal completion
            if not executor._shutdown:
                executor.shutdown(wait=True)

        if not silent:
            if success_count == total_count:
                print(f"All {total_count} versions installed successfully!")
            else:
                print(f"{success_count}/{total_count} versions installed successfully")

        return success_count == total_count
