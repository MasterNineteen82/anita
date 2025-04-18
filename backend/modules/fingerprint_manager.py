import logging
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional, Union
import time

# Import centralized models
from backend.models import BiometricData, BiometricMatchResult, BiometricType
from backend.models import SuccessResponse, ErrorResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FingerprintManager:
    def __init__(self):
        self.fingerprints: Dict[str, BiometricData] = {}  # Store BiometricData objects

    async def enroll(self, user_id: str, biometric_data: BiometricData) -> SuccessResponse:
        """
        Enroll a new fingerprint for a user.

        Args:
            user_id: Unique identifier for the user
            biometric_data: BiometricData object representing the user's fingerprint

        Returns:
            SuccessResponse: Result of the enrollment
        """
        if biometric_data.biometric_type != BiometricType.FINGERPRINT:
            return ErrorResponse(
                status="error",
                message="Incorrect biometric type. Expected FINGERPRINT."
            )

        if user_id in self.fingerprints:
            logger.warning(f"User {user_id} already has a fingerprint enrolled.")
            return ErrorResponse(
                status="error",
                message=f"User {user_id} already has a fingerprint enrolled."
            )

        self.fingerprints[user_id] = biometric_data
        logger.info(f"Fingerprint enrolled for user {user_id}.")
        return SuccessResponse(
            status="success",
            message=f"Fingerprint enrolled for user {user_id}."
        )

    async def verify(self, user_id: str, biometric_data: BiometricData) -> SuccessResponse:
        """
        Verify a user's fingerprint.

        Args:
            user_id: Unique identifier for the user
            biometric_data: BiometricData object representing the user's fingerprint

        Returns:
            SuccessResponse: Verification result
        """

        if biometric_data.biometric_type != BiometricType.FINGERPRINT:
            return ErrorResponse(
                status="error",
                message="Incorrect biometric type. Expected FINGERPRINT."
            )

        if user_id not in self.fingerprints:
            logger.error(f"No fingerprint found for user {user_id}.")
            return ErrorResponse(
                status="error",
                message=f"No fingerprint found for user {user_id}."
            )

        stored_fingerprint_data = self.fingerprints[user_id]
        if stored_fingerprint_data.data == biometric_data.data:
            logger.info(f"Fingerprint verified successfully for user {user_id}.")
            match_result = BiometricMatchResult(is_match=True, confidence=0.9)
            return SuccessResponse(
                status="success",
                message="Fingerprint verified successfully.",
                data=match_result.model_dump()
            )
        else:
            logger.error(f"Fingerprint verification failed for user {user_id}.")
            match_result = BiometricMatchResult(is_match=False, confidence=0.1)
            return SuccessResponse(
                status="success",
                message="Fingerprint verification failed.",
                data=match_result.model_dump()
            )

    async def delete(self, user_id: str) -> SuccessResponse:
        """
        Delete a user's fingerprint.

        Args:
            user_id: Unique identifier for the user

        Returns:
            SuccessResponse: Result of the deletion
        """
        if user_id not in self.fingerprints:
            logger.error(f"No fingerprint found for user {user_id}.")
            return ErrorResponse(
                status="error",
                message=f"No fingerprint found for user {user_id}."
            )

        del self.fingerprints[user_id]
        logger.info(f"Fingerprint deleted for user {user_id}.")
        return SuccessResponse(
            status="success",
            message=f"Fingerprint deleted for user {user_id}."
        )

# Example usage
if __name__ == "__main__":
    async def main():
        manager = FingerprintManager()
        # Create a BiometricData object for enrollment
        enrollment_data = BiometricData(biometric_type=BiometricType.FINGERPRINT, data="fingerprint_data_1")
        enroll_result = await manager.enroll("user1", enrollment_data)
        print(enroll_result)

        # Create a BiometricData object for verification
        verification_data = BiometricData(biometric_type=BiometricType.FINGERPRINT, data="fingerprint_data_1")
        verify_result = await manager.verify("user1", verification_data)
        print(verify_result)

        delete_result = await manager.delete("user1")
        print(delete_result)

        # Try to verify again after deletion
        verify_result = await manager.verify("user1", verification_data)
        print(verify_result)
    asyncio.run(main())
