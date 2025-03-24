import random
import logging
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from smartcard.System import readers
from smartcard.Exceptions import NoCardException
from fastapi import HTTPException
from backend.models import CardData, SuccessResponse, ErrorResponse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s')

SIMULATION_MODE = os.environ.get('SIMULATION_MODE', 'False').lower() == 'true'
SIMULATION_READER_COUNT = int(os.environ.get('SIMULATION_READER_COUNT', '2'))
SIMULATION_CARD_PRESENT_PROBABILITY = float(os.environ.get('SIMULATION_CARD_PRESENT_PROBABILITY', '0.7'))

class CardManager:
    executor = ThreadPoolExecutor()

    @staticmethod
    async def detect_card():
        logging.info("Detecting card presence...")
        if SIMULATION_MODE:
            logging.info(f"Running in simulation mode with {SIMULATION_READER_COUNT} readers.")
            for i in range(SIMULATION_READER_COUNT):
                if random.random() < SIMULATION_CARD_PRESENT_PROBABILITY:
                    return SuccessResponse(
                        status="success",
                        data={'active_reader': i}
                    )
            return SuccessResponse(
                status="success",
                data={'active_reader': None}
            )

        loop = asyncio.get_event_loop()
        try:
            available_readers = await loop.run_in_executor(None, readers)
            if not available_readers:
                raise HTTPException(status_code=404, detail="No smartcard readers found")

            for i, reader in enumerate(available_readers):
                conn = reader.createConnection()
                try:
                    await loop.run_in_executor(None, conn.connect)
                    await loop.run_in_executor(None, conn.disconnect)
                    return SuccessResponse(
                        status="success",
                        data={'active_reader': i}
                    )
                except NoCardException:
                    continue
            return SuccessResponse(
                status="success",
                data={'active_reader': None}
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_card_config(card_type: str):
        """
        Retrieves the configuration for a specific card type.

        Args:
            card_type (str): The type of card to retrieve the configuration for.

        Returns:
            dict: A dictionary containing the status and the card configuration data.

        Raises:
            HTTPException:
                - 400: If the card_type is not provided.
                - 404: If the card configuration is not found for the given card_type.
                - 500: If any other unexpected error occurs.
        """
        logging.info(f"Getting card config for type: {card_type}")
        if not card_type:
            logging.error("Card type is required.")
            raise HTTPException(status_code=400, detail="Card type required")

        # Simulate retrieving card configuration from a database or file
        config_data = await CardManager._retrieve_config_from_source(card_type)

        if config_data is None:
            logging.warning(f"No config found for card type: {card_type}")
            raise HTTPException(status_code=404, detail=f"No config found for card type: {card_type}")

        return {'status': 'success', 'data': {'config': config_data}}

    @staticmethod
    async def set_card_config(card_type: str, config: dict):
        """
        Sets the configuration for a specific card type.

        Args:
            card_type (str): The type of card to set the configuration for.
            config (dict): The configuration data to set.

        Returns:
            dict: A dictionary containing the status and a success message.

        Raises:
            HTTPException:
                - 400: If the card_type or config is not provided or if the config is invalid.
                - 500: If any other unexpected error occurs during the configuration setting.
        """
        logging.info(f"Setting card config for type: {card_type} with config: {config}")
        if not card_type or not config:
            logging.error("Card type and config are required.")
            raise HTTPException(status_code=400, detail="Card type and config required")

        if not isinstance(config, dict):
            logging.error("Config must be a dictionary.")
            raise HTTPException(status_code=400, detail="Config must be a dictionary")

        # Simulate saving the card configuration to a database or file
        try:
            await CardManager._save_config_to_source(card_type, config)
        except Exception as e:
            logging.error(f"Error saving config for card type {card_type}: {e}")
            raise HTTPException(status_code=500, detail=f"Error saving config: {str(e)}")

        return {'status': 'success', 'data': {'message': f"Config set for {card_type}"}}

    @staticmethod
    async def factory_reset(card_type: str):
        """
        Resets the configuration for a specific card type to its factory defaults.

        Args:
            card_type (str): The type of card to reset.

        Returns:
            dict: A dictionary containing the status and a success message.

        Raises:
            HTTPException:
                - 400: If the card_type is not provided.
                - 500: If any other unexpected error occurs during the reset.
        """
        logging.info(f"Performing factory reset for card type: {card_type}")
        if not card_type:
            logging.error("Card type is required.")
            raise HTTPException(status_code=400, detail="Card type required")

        # Simulate resetting the card configuration to factory defaults
        try:
            await CardManager._reset_config_to_default(card_type)
        except Exception as e:
            logging.error(f"Error during factory reset for card type {card_type}: {e}")
            raise HTTPException(status_code=500, detail=f"Error during factory reset: {str(e)}")

        return {'status': 'success', 'data': {'message': f"Factory reset for {card_type}"}}

    @staticmethod
    async def _retrieve_config_from_source(card_type: str):
        """
        Simulates retrieving card configuration from a data source (e.g., database, file).
        In a real implementation, this method would interact with a persistent storage.
        """
        # Placeholder: Replace with actual data retrieval logic
        if card_type == "TypeA":
            return {"param1": "value1", "param2": "value2"}
        elif card_type == "TypeB":
            return {"param3": "value3", "param4": "value4"}
        else:
            return None

    @staticmethod
    async def _save_config_to_source(card_type: str, config: dict):
        """
        Simulates saving card configuration to a data source.
        In a real implementation, this method would interact with a persistent storage.
        """
        # Placeholder: Replace with actual data saving logic
        logging.info(f"Saving config {config} for card type: {card_type} to source.")
        # Simulate a delay to represent I/O operation
        await asyncio.sleep(0.1)

    @staticmethod
    async def _reset_config_to_default(card_type: str):
        """
        Simulates resetting card configuration to default values.
        In a real implementation, this method would update the persistent storage with default values.
        """
        # Placeholder: Replace with actual reset logic
        logging.info(f"Resetting config to default for card type: {card_type}.")
        # Simulate a delay to represent I/O operation
        await asyncio.sleep(0.1)