import re
import requests
from typing import Dict, Optional, Any
import logging
from urllib.parse import urlencode
import webbrowser

logger = logging.getLogger(__name__)

class ComplaintHandler:
    def __init__(self):
        self.complaint_base_url = "https://grs.ietlucknow.ac.in/open.php"
        self.complaint_states = {}  # Store complaint collection states for different users
        
    def detect_complaint(self, message: str) -> bool:
        """Detect if the message contains a complaint."""
        complaint_keywords = [
            # Infrastructure issues
            'fan not working', 'fan broken', 'fan issue', 'ceiling fan',
            'light not working', 'light broken', 'bulb not working', 'electricity',
            'water problem', 'no water', 'tap not working', 'plumbing',
            'wifi', 'wi-fi', 'internet', 'network', 'connection',
            'ac not working', 'air conditioner', 'cooling problem',
            'door broken', 'lock issue', 'window broken',
            
            # Cleanliness and maintenance
            'room dirty', 'bathroom dirty', 'cleaning issue', 'garbage',
            'pest problem', 'insects', 'cockroach', 'rats',
            'paint peeling', 'wall damage', 'ceiling leak',
            
            # Mess and food issues
            'food quality', 'mess problem', 'bad food', 'food complaint',
            'hygiene issue', 'kitchen problem',
            
            # Hostel services
            'laundry problem', 'security issue', 'noise complaint',
            'common room', 'study room issue',
            
            # General complaint phrases
            'complain', 'complaint', 'problem', 'issue', 'broken',
            'not working', 'malfunctioning', 'damaged', 'faulty'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in complaint_keywords)
    
    def get_complaint_category(self, message: str) -> str:
        """Categorize the complaint based on the message content."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['fan', 'light', 'bulb', 'electricity', 'ac', 'air conditioner']):
            return "Electrical"
        elif any(word in message_lower for word in ['water', 'tap', 'plumbing', 'bathroom', 'toilet']):
            return "Plumbing"
        elif any(word in message_lower for word in ['wifi', 'internet', 'network']):
            return "Internet/WiFi"
        elif any(word in message_lower for word in ['food', 'mess', 'kitchen', 'hygiene']):
            return "Mess/Food"
        elif any(word in message_lower for word in ['cleaning', 'dirty', 'garbage', 'pest']):
            return "Cleanliness"
        elif any(word in message_lower for word in ['door', 'window', 'lock', 'paint', 'wall', 'ceiling']):
            return "Infrastructure"
        elif any(word in message_lower for word in ['noise', 'security', 'common room']):
            return "Hostel Services"
        else:
            return "General"
    
    def start_complaint_collection(self, user_session: str, complaint_text: str) -> Dict[str, Any]:
        """Start collecting complaint details from the user."""
        complaint_category = self.get_complaint_category(complaint_text)
        
        self.complaint_states[user_session] = {
            'step': 'collect_name',
            'complaint_text': complaint_text,
            'category': complaint_category,
            'details': {}
        }
        
        return {
            'message': f"I'm sorry to hear about this {complaint_category.lower()} issue. I'll help you register a complaint. Let me collect some basic information first.\n\nPlease provide your full name:",
            'needs_input': True,
            'step': 'collect_name'
        }
    
    def process_complaint_step(self, user_session: str, user_input: str) -> Dict[str, Any]:
        """Process each step of complaint collection."""
        if user_session not in self.complaint_states:
            return {'message': "Please start by describing your complaint.", 'needs_input': True}
        
        state = self.complaint_states[user_session]
        current_step = state['step']
        
        if current_step == 'collect_name':
            state['details']['name'] = user_input.strip()
            state['step'] = 'collect_email'
            return {
                'message': f"Thank you, {user_input}. Now please provide your college email address:",
                'needs_input': True,
                'step': 'collect_email'
            }
        
        elif current_step == 'collect_email':
            email = user_input.strip()
            if not self._validate_email(email):
                return {
                    'message': "Please provide a valid email address (preferably your college email):",
                    'needs_input': True,
                    'step': 'collect_email'
                }
            state['details']['email'] = email
            state['step'] = 'collect_phone'
            return {
                'message': "Great! Now please provide your phone number:",
                'needs_input': True,
                'step': 'collect_phone'
            }
        
        elif current_step == 'collect_phone':
            phone = user_input.strip()
            if not self._validate_phone(phone):
                return {
                    'message': "Please provide a valid 10-digit phone number:",
                    'needs_input': True,
                    'step': 'collect_phone'
                }
            state['details']['phone'] = phone
            state['step'] = 'collect_room'
            return {
                'message': "Thank you! Please provide your room number:",
                'needs_input': True,
                'step': 'collect_room'
            }
        
        elif current_step == 'collect_room':
            state['details']['room_number'] = user_input.strip()
            state['step'] = 'complete'
            
            # Generate the complaint summary and next steps
            return self._complete_complaint_collection(user_session)
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _validate_phone(self, phone: str) -> bool:
        """Validate phone number format."""
        # Remove any non-digit characters
        phone_digits = re.sub(r'\D', '', phone)
        # Check if it's 10 digits (Indian mobile) or 10 digits with country code
        return len(phone_digits) >= 10 and len(phone_digits) <= 12
    
    def _complete_complaint_collection(self, user_session: str) -> Dict[str, Any]:
        """Complete the complaint collection and provide next steps."""
        state = self.complaint_states[user_session]
        details = state['details']
        
        # Prepare complaint summary
        complaint_summary = f"""
📋 **Complaint Summary**

**Issue Category:** {state['category']}
**Description:** {state['complaint_text']}

**Your Details:**
- **Name:** {details['name']}
- **Email:** {details['email']}
- **Phone:** {details['phone']}
- **Room Number:** {details['room_number']}

✅ **Next Steps:**
1. Click the link below to open the complaint portal
2. The form will try to auto-fill your basic information
3. Please manually enter the following details if not pre-filled:
   - **Email Address:** {details['email']}
   - **Full Name:** {details['name']}
   - **Phone Number:** {details['phone']}
   - **Problem Summary:** Room {details['room_number']} - {state['complaint_text']}
   - **Location:** Room {details['room_number']}
4. Add any additional details in the description field
5. Submit the complaint to receive a reference number

💡 **Tip:** Keep this chat open for reference while filling the form!
"""
        
        # Generate the pre-filled URL
        complaint_url = self._generate_complaint_url(state)
        
        # Clean up the session
        del self.complaint_states[user_session]
        
        return {
            'message': complaint_summary,
            'complaint_url': complaint_url,
            'needs_input': False,
            'step': 'complete',
            'redirect': True,
            'user_details': details,  # Include details for manual reference
            'complaint_info': {
                'category': state['category'],
                'description': state['complaint_text'],
                'room': details['room_number']
            }
        }
    
    def _generate_complaint_url(self, state: Dict) -> str:
        """Generate URL with pre-filled parameters for the complaint portal."""
        details = state['details']
        
        # Based on common form field patterns and osTicket system
        # These are the most likely field names for the form
        problem_summary = f"Room {details['room_number']} - {state['complaint_text']}"
        
        # Try multiple possible parameter combinations
        # Common field names in osTicket and web forms
        possible_params = [
            # osTicket common field names
            {
                'email': details['email'],
                'name': details['name'], 
                'fullname': details['name'],
                'phone': details['phone'],
                'mobile': details['phone'],
                'subject': problem_summary[:100],
                'summary': problem_summary[:100],
                'message': state['complaint_text'],
                'issue': state['complaint_text'],
                'location': f"Room {details['room_number']}",
                'room': details['room_number']
            },
            # Alternative field names
            {
                'user_email': details['email'],
                'user_name': details['name'],
                'contact_phone': details['phone'],
                'problem_summary': problem_summary[:100],
                'problem_location': f"Room {details['room_number']}"
            }
        ]
        
        # Use the first set of parameters
        params = possible_params[0]
        
        # Clean up None values and encode
        clean_params = {k: v for k, v in params.items() if v is not None and v != ''}
        
        # Build the URL
        base_url = self.complaint_base_url
        query_string = urlencode(clean_params)
        
        return f"{base_url}?{query_string}"
    
    def is_in_complaint_flow(self, user_session: str) -> bool:
        """Check if user is currently in complaint collection flow."""
        return user_session in self.complaint_states
    
    def get_current_step(self, user_session: str) -> Optional[str]:
        """Get the current step in complaint collection."""
        if user_session in self.complaint_states:
            return self.complaint_states[user_session]['step']
        return None
    
    def cancel_complaint(self, user_session: str) -> str:
        """Cancel the current complaint collection process."""
        if user_session in self.complaint_states:
            del self.complaint_states[user_session]
            return "Complaint registration cancelled. How else can I help you?"
        return "No active complaint registration to cancel."
