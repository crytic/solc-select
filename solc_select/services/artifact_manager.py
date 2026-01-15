"""Artifact management service for solc-select."""

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from io import BufferedRandom
from zipfile import ZipFile

import requests
from Crypto.Hash import keccak

from ..exceptions import ChecksumMismatchError, SolcSelectError
from ..infrastructure.filesystem import FilesystemManager
from ..models.artifacts import SolcArtifact, SolcArtifactOnDisk
from ..models.platforms import Platform
from ..models.versions import SolcVersion
from ..platform_capabilities import PlatformCapability
from .repository_matcher import RepositoryMatcher


class ArtifactManager:
    """Service for managing Solidity compiler artifacts."""

    def __init__(
        self,
        repository_matcher: RepositoryMatcher,
        platform_capability: PlatformCapability,
        platform: Platform,
        session: requests.Session,
        filesystem: FilesystemManager | None = None,
    ):
        self.repository_matcher = repository_matcher
        self.platform_capability = platform_capability
        self.platform = platform
        self.session = session
        self.filesystem = filesystem or FilesystemManager()

    def create_local_artifact_metadata(self, version: SolcVersion) -> SolcArtifactOnDisk:
        """Create artifact metadata for a locally available version."""
        _, target_platform = self.repository_matcher.find_repository_for_version(
            version, exact=False
        )
        binary_path = self.filesystem.get_binary_path(version)
        emulation = self.platform_capability.get_emulation_for_platform(target_platform)

        return SolcArtifactOnDisk(
            version=version,
            platform=self.platform,
            file_path=binary_path,
            emulation=emulation,
        )

    def create_artifact_metadata(self, version: SolcVersion) -> SolcArtifact:
        """Create artifact metadata for a version."""
        repo, target_platform = self.repository_matcher.find_repository_for_version(version)
        binary_path = self.filesystem.get_binary_path(version)
        emulation = self.platform_capability.get_emulation_for_platform(target_platform)

        available = repo.available_versions
        version_str = str(version)
        if version_str not in available:
            raise ValueError(f"Version {version} is not available")

        artifact_filename = available[version_str]
        download_url = repo.get_download_url(artifact_filename)
        sha256_hash, keccak256_hash = repo.get_checksums(version)

        return SolcArtifact(
            version=version,
            platform=self.platform,
            download_url=download_url,
            checksum_sha256=sha256_hash,
            checksum_keccak256=keccak256_hash,
            file_path=binary_path,
            emulation=emulation,
        )

    def verify_checksum(self, artifact: SolcArtifact, file_handle: BufferedRandom) -> None:
        """Verify the checksums of a downloaded artifact."""
        sha256_factory = hashlib.sha256()
        keccak_factory = keccak.new(digest_bits=256)

        file_handle.seek(0)
        for chunk in iter(lambda: file_handle.read(1024000), b""):  # 1MB chunks
            sha256_factory.update(chunk)
            keccak_factory.update(chunk)

        local_sha256 = sha256_factory.hexdigest()
        local_keccak256 = keccak_factory.hexdigest()

        if artifact.checksum_sha256 != local_sha256:
            raise ChecksumMismatchError(artifact.checksum_sha256, local_sha256, "SHA256")

        if artifact.checksum_keccak256 and artifact.checksum_keccak256 != local_keccak256:
            raise ChecksumMismatchError(artifact.checksum_keccak256, local_keccak256, "Keccak256")

    def _download_artifact(self, artifact: SolcArtifact) -> None:
        """Download artifact and verify checksums."""
        response = self.session.get(artifact.download_url, stream=True)
        response.raise_for_status()

        try:
            with open(artifact.file_path, "w+b", opener=partial(os.open, mode=0o664)) as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                self.verify_checksum(artifact, f)
        except KeyboardInterrupt:
            if artifact.file_path.exists():
                artifact.file_path.unlink(missing_ok=True)
            raise

    def download_and_install(self, version: SolcVersion, silent: bool = False) -> bool:
        """Download and install a Solidity compiler version."""
        if self.filesystem.is_installed(version):
            if not silent:
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

        self.filesystem.ensure_artifact_directory(version)

        try:
            self._download_artifact(artifact)

            if artifact.is_zip_archive:
                self._extract_zip_archive(artifact)
            else:
                artifact.file_path.chmod(0o775)

            if not silent:
                print(f"Version '{version}' installed.")

            return True

        except ChecksumMismatchError:
            if artifact.file_path.exists():
                artifact.file_path.unlink()
            raise

        except Exception as e:
            if artifact.file_path.exists():
                artifact.file_path.unlink()
            if not silent:
                print(f"Error installing {version}: {e}")
            return False

    def _extract_zip_archive(self, artifact: SolcArtifact) -> None:
        """Extract a ZIP archive and rename the binary."""
        artifact_dir = artifact.file_path.parent

        with ZipFile(artifact.file_path, "r") as zip_ref:
            zip_ref.extractall(path=artifact_dir)

        artifact.file_path.unlink()
        extracted_binary = artifact_dir / artifact.get_binary_name_in_zip()
        extracted_binary.rename(artifact.file_path)
        artifact.file_path.chmod(0o775)

    def install_versions(self, versions: list[SolcVersion], silent: bool = False) -> bool:
        """Install multiple versions concurrently."""
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

        if not silent:
            print(f"Installing {len(versions)} versions concurrently...")

        success_count = 0
        total_count = len(versions)

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_version = {
                executor.submit(self.download_and_install, version, True): version
                for version in versions
            }

            try:
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
                    print("\nCancelling installation...")
                # Cancel all pending futures before exiting
                for future in future_to_version:
                    future.cancel()
                raise

        if not silent:
            if success_count == total_count:
                print(f"All {total_count} versions installed successfully!")
            else:
                print(f"{success_count}/{total_count} versions installed successfully")

        return success_count == total_count
