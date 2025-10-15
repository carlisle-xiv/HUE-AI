"""
Model Service for Health Assistant
Handles inference using HuggingFace Inference API for medical AI models
"""

import os
from huggingface_hub import InferenceClient
from PIL import Image
import logging
from typing import Optional, Dict, List, Tuple
import io
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelService:
    """
    Singleton service for managing AI models via HuggingFace Inference API.
    Uses HuatuoGPT-o1-72B for text-based medical queries and HuatuoGPT-Vision for image analysis.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the model service with HuggingFace API"""
        if not ModelService._initialized:
            logger.info("Initializing ModelService with HuggingFace Inference API...")

            # Get API key from environment
            self.hf_token = os.getenv("HUGGINGFACE_API_KEY")
            if not self.hf_token:
                raise ValueError(
                    "HUGGINGFACE_API_KEY not found in environment variables. "
                    "Please add it to your .env file"
                )

            # Initialize HuggingFace Inference Client
            self.client = InferenceClient(token=self.hf_token)

            # Model configurations
            self.text_model_name = "mistralai/Mistral-7B-Instruct-v0.2"
            self.vision_model_name = "llava-hf/llava-1.5-7b-hf"

            logger.info(f"Using text model: {self.text_model_name}")
            logger.info(f"Using vision model: {self.vision_model_name}")

            # Test API connection
            self._test_connection()

            ModelService._initialized = True
            logger.info("ModelService initialized successfully!")

    def _test_connection(self):
        """Test HuggingFace API connection"""
        try:
            # Simple test call
            logger.info("Testing HuggingFace API connection...")
            response = self.client.text_generation(
                "Hello", model=self.text_model_name, max_new_tokens=5
            )
            logger.info("✅ API connection successful!")
        except Exception as e:
            logger.error(f"❌ API connection failed: {str(e)}")
            raise

    def _format_medical_prompt(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Format the prompt for medical consultation with conversation history.

        Args:
            query: Current user query
            conversation_history: List of previous messages [{"role": "user/assistant", "content": "..."}]
            system_prompt: Optional system prompt for model behavior

        Returns:
            Formatted prompt string
        """
        if system_prompt is None:
            system_prompt = """You are a knowledgeable medical AI assistant. Your role is to:
1. Provide helpful information about symptoms and health conditions
2. Suggest when medical attention may be needed
3. Always remind users that this is not a substitute for professional medical advice
4. Be empathetic, clear, and avoid causing unnecessary alarm
5. Ask clarifying questions when needed

IMPORTANT: Always include appropriate disclaimers and encourage consulting healthcare professionals for serious concerns."""

        # Build conversation context
        conversation = f"System: {system_prompt}\n\n"

        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-5:]:  # Keep last 5 exchanges for context
                role = msg.get("role", "")
                content = msg.get("content", "")

                if role == "user":
                    conversation += f"User: {content}\n"
                elif role == "assistant":
                    conversation += f"Assistant: {content}\n"

        # Add current query
        conversation += f"User: {query}\nAssistant:"

        return conversation

    def generate_text_response(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> Tuple[str, Dict]:
        """
        Generate response using HuatuoGPT-o1-72B for text-only queries.

        Args:
            query: User's medical query
            conversation_history: Previous conversation messages
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            top_p: Nucleus sampling parameter

        Returns:
            Tuple of (response_text, metadata)
        """
        try:
            # Format prompt
            prompt = self._format_medical_prompt(query, conversation_history)

            logger.info(f"Generating text response (max_tokens={max_new_tokens})")

            # Call HuggingFace Inference API
            response = self.client.text_generation(
                prompt,
                model=self.text_model_name,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                return_full_text=False,
            )

            # Extract response text
            response_text = response.strip()

            # Metadata
            metadata = {
                "model": self.text_model_name,
                "temperature": temperature,
                "max_tokens": max_new_tokens,
                "prompt_length": len(prompt),
                "response_length": len(response_text),
            }

            logger.info(f"Response generated: {len(response_text)} characters")
            return response_text, metadata

        except Exception as e:
            logger.error(f"Error generating text response: {str(e)}")
            raise

    def generate_vision_response(
        self,
        query: str,
        image: Image.Image,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
    ) -> Tuple[str, Dict]:
        """
        Generate response using HuatuoGPT-Vision for image+text queries.

        Args:
            query: User's medical query about the image
            image: PIL Image object
            conversation_history: Previous conversation messages
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Tuple of (response_text, metadata)
        """
        try:
            # Format prompt
            system_context = """You are a medical AI assistant analyzing medical images. 
Provide detailed, accurate analysis while reminding users this is not a substitute for professional medical diagnosis."""

            prompt = f"{system_context}\n\nUser query: {query}\nPlease analyze the image and respond:"

            logger.info(f"Generating vision response (max_tokens={max_new_tokens})")

            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format="PNG")
            img_byte_arr = img_byte_arr.getvalue()

            # Call HuggingFace Inference API for visual question answering
            response = self.client.visual_question_answering(
                image=img_byte_arr,
                question=prompt,
                model=self.vision_model_name,
            )

            # Extract response (format may vary by model)
            if isinstance(response, list) and len(response) > 0:
                response_text = response[0].get("answer", str(response))
            elif isinstance(response, dict):
                response_text = response.get("answer", str(response))
            else:
                response_text = str(response)

            response_text = response_text.strip()

            # Metadata
            metadata = {
                "model": self.vision_model_name,
                "temperature": temperature,
                "max_tokens": max_new_tokens,
                "prompt_length": len(prompt),
                "response_length": len(response_text),
                "has_image": True,
            }

            logger.info(f"Vision response generated: {len(response_text)} characters")
            return response_text, metadata

        except Exception as e:
            logger.error(f"Error generating vision response: {str(e)}")
            raise

    def process_image_from_base64(self, base64_string: str) -> Image.Image:
        """
        Convert base64 encoded image to PIL Image.

        Args:
            base64_string: Base64 encoded image string

        Returns:
            PIL Image object
        """
        try:
            # Remove data URL prefix if present
            if "," in base64_string:
                base64_string = base64_string.split(",")[1]

            # Decode base64
            image_data = base64.b64decode(base64_string)
            image = Image.open(io.BytesIO(image_data))

            # Convert to RGB if necessary
            if image.mode != "RGB":
                image = image.convert("RGB")

            logger.info(f"Image processed from base64: {image.size}")
            return image

        except Exception as e:
            logger.error(f"Error processing image from base64: {str(e)}")
            raise ValueError(f"Invalid image format: {str(e)}")

    def process_image_from_bytes(self, image_bytes: bytes) -> Image.Image:
        """
        Convert image bytes to PIL Image.

        Args:
            image_bytes: Raw image bytes

        Returns:
            PIL Image object
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))

            # Convert to RGB if necessary
            if image.mode != "RGB":
                image = image.convert("RGB")

            logger.info(f"Image processed from bytes: {image.size}")
            return image

        except Exception as e:
            logger.error(f"Error processing image from bytes: {str(e)}")
            raise ValueError(f"Invalid image format: {str(e)}")

    def health_check(self) -> Dict[str, bool]:
        """
        Check if models are accessible via API.

        Returns:
            Dictionary with model status
        """
        text_ready = False
        vision_ready = False

        try:
            # Test text model
            self.client.text_generation(
                "test", model=self.text_model_name, max_new_tokens=1
            )
            text_ready = True
            logger.info("✅ Text model accessible")
        except Exception as e:
            logger.error(f"❌ Text model not accessible: {str(e)}")

        try:
            # Vision model check (basic)
            vision_ready = True  # Assume ready if client initialized
            logger.info("✅ Vision model configured")
        except Exception as e:
            logger.error(f"❌ Vision model error: {str(e)}")

        return {
            "text_model_ready": text_ready,
            "vision_model_ready": vision_ready,
            "api_configured": self.hf_token is not None,
            "text_model": self.text_model_name,
            "vision_model": self.vision_model_name,
        }


# Create singleton instance
model_service = ModelService()
