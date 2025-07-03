import os
from typing import Dict, List, Optional
import logging
import re
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class HostelPhotos:
    def __init__(self, photos_directory: str = "hostel_photos"):
        """Initialize the photos manager with a directory path."""
        self.photos_directory = Path(photos_directory)
        self.photo_categories = {
            "rooms": ["rooms"],
            "mess": ["dining"],
            "facilities": ["sports"],
            "exterior": ["building", "entrance", "garden"]
        }
        
    def setup(self) -> bool:
        """Ensure the photos directory exists and is properly structured."""
        try:
            # Create main photos directory if it doesn't exist
            self.photos_directory.mkdir(exist_ok=True)
            
            # Create category subdirectories
            for category in self.photo_categories:
                category_dir = self.photos_directory / category
                category_dir.mkdir(exist_ok=True)
                
                # Create subcategory directories
                for subcategory in self.photo_categories[category]:
                    subcategory_dir = category_dir / subcategory
                    subcategory_dir.mkdir(exist_ok=True)
            
            return True
        except Exception as e:
            logger.error(f"Failed to setup photos directory structure: {str(e)}")
            return False

    def get_photo_paths(self, category: Optional[str] = None, subcategory: Optional[str] = None) -> List[str]:
        """
        Get paths to photos based on category and subcategory.
        Returns a list of photo paths matching the criteria.
        """
        try:
            photo_paths = []
            
            if category and subcategory:
                # Get specific subcategory photos
                photo_dir = self.photos_directory / category / subcategory
                if photo_dir.exists():
                    photo_paths.extend([str(p) for p in photo_dir.glob("*.jpg")])
                    photo_paths.extend([str(p) for p in photo_dir.glob("*.png")])
            elif category:
                # Get all photos in a category
                category_dir = self.photos_directory / category
                if category_dir.exists():
                    for subcategory in self.photo_categories.get(category, []):
                        photo_dir = category_dir / subcategory
                        photo_paths.extend([str(p) for p in photo_dir.glob("*.jpg")])
                        photo_paths.extend([str(p) for p in photo_dir.glob("*.png")])
            else:
                # Get all hostel photos
                for category_dir in self.photos_directory.iterdir():
                    if category_dir.is_dir():
                        for subcategory_dir in category_dir.iterdir():
                            if subcategory_dir.is_dir():
                                photo_paths.extend([str(p) for p in subcategory_dir.glob("*.jpg")])
                                photo_paths.extend([str(p) for p in subcategory_dir.glob("*.png")])
            
            return photo_paths
            
        except Exception as e:
            logger.error(f"Error getting photo paths: {str(e)}")
            return []

    def handle_photo_query(self, question: str) -> Optional[List[str]]:
        """
        Handle questions related to hostel photos.
        Returns a list of relevant photo paths or None if query isn't photo-related.
        """
        try:
            question_lower = question.lower()
            
            # Check if the question is asking for photos
            photo_keywords = r"(photo|picture|image|pic|show me|look|view)"
            if not re.search(photo_keywords, question_lower):
                return None
                
            # Check for specific categories
            photos_to_return = []
            
            for category, subcategories in self.photo_categories.items():
                if category in question_lower:
                    # Check for specific subcategories
                    for subcategory in subcategories:
                        if subcategory.replace("_", " ") in question_lower:
                            photos = self.get_photo_paths(category, subcategory)
                            if photos:
                                photos_to_return.extend(photos)
                                
                    # If no specific subcategory mentioned, get all category photos
                    if not photos_to_return:
                        photos_to_return.extend(self.get_photo_paths(category))
                        
            # If no specific category found but asking for hostel photos
            if not photos_to_return and re.search(r"(hostel|building|campus)", question_lower):
                photos_to_return.extend(self.get_photo_paths())
            
            return photos_to_return if photos_to_return else None
            
        except Exception as e:
            logger.error(f"Error handling photo query: {str(e)}")
            return None

    def get_photos(self, category: str, subcategory: Optional[str] = None) -> List[str]:
        """
        A tool to get paths to hostel photos.
        :param category: The category of photos to get. Must be one of ['rooms', 'mess', 'facilities', 'exterior'].
        :param subcategory: The optional subcategory of photos.
                            For 'mess', can be ['dining'].
                            For 'facilities', can be ['sports'].
                            For 'exterior', can be ['building', 'entrance', 'garden'].
        :return: A list of photo paths.
        """
        if category not in self.photo_categories:
            return [f"Invalid category '{category}'. Valid categories are: {list(self.photo_categories.keys())}"]

        if subcategory:
            if subcategory not in self.photo_categories.get(category, []):
                return [f"Invalid subcategory '{subcategory}' for category '{category}'. Valid subcategories are: {self.photo_categories.get(category)}"]
            return self.get_photo_paths(category, subcategory)
        else:
            return self.get_photo_paths(category)

def test_photo_handling():
    """Test function to verify photo queries."""
    photo_manager = HostelPhotos()
    photo_manager.setup()
    
    test_questions = [
        "Show me the hostel rooms",
        "Can I see pictures of the mess?",
        "I want to see the hostel building",
        "Pictures of double rooms please",
        "Show me the library photos"
    ]
    
    for question in test_questions:
        print(f"\nQuery: {question}")
        photos = photo_manager.handle_photo_query(question)
        if photos:
            print(f"Found photos: {len(photos)} photos")
            for photo in photos[:3]:  # Show first 3 paths
                print(f"- {photo}")
        else:
            print("No relevant photos found")


if __name__ == "__main__":
    test_photo_handling()