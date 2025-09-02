import firebase_admin
from firebase_admin import credentials, auth
import os
import json
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global variable to track initialization status
firebase_initialized = False

# Initialize Firebase Admin SDK
def initialize_firebase():
    global firebase_initialized
    
    if firebase_initialized:
        print("Firebase Admin SDK already initialized")
        return
    
    try:
        # Get service account file path from environment variable
        service_account_key = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY')
        
        if not service_account_key:
            print("Error: FIREBASE_SERVICE_ACCOUNT_KEY environment variable not set")
            firebase_initialized = False
            return
        
        # Handle both absolute and relative paths
        if os.path.isabs(service_account_key):
            service_account_path = service_account_key
        else:
            # If it's a relative path, assume it's relative to the backend directory
            service_account_path = os.path.join(os.path.dirname(__file__), service_account_key)
        
        if not os.path.exists(service_account_path):
            print(f"Error: Service account file not found at: {service_account_path}")
            firebase_initialized = False
            return
        
        # Read the service account file to get the project ID
        with open(service_account_path, 'r') as f:
            service_account_data = json.load(f)
            project_id = service_account_data.get('project_id')
        
        # Initialize with service account file and project ID
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred, {
            'projectId': project_id
        })
        print(f"Firebase Admin SDK initialized with service account: {service_account_path}")
        firebase_initialized = True
            
    except Exception as e:
        print(f"Error initializing Firebase Admin SDK: {e}")
        print(traceback.format_exc())
        firebase_initialized = False

# Initialize Firebase on module import
initialize_firebase()

def verify_firebase_token(token):
    """
    Verify a Firebase ID token
    
    Args:
        token (str): The Firebase ID token to verify
        
    Returns:
        dict: The decoded token claims if valid, None otherwise
    """
    global firebase_initialized
    
    # Ensure Firebase is initialized
    if not firebase_initialized:
        print("Firebase not initialized, attempting to initialize now")
        initialize_firebase()
        
        if not firebase_initialized:
            print("Failed to initialize Firebase, cannot verify token")
            return None
    
    try:
        # Verify the token
        decoded_token = auth.verify_id_token(token)
        
        # Check if the email domain is bellingcat.com
        email = decoded_token.get('email', '')
        if not email.endswith('@bellingcat.com'):
            print(f"Access denied: Email domain not allowed: {email}")
            return None
            
        return decoded_token
    except Exception as e:
        print(f"Error verifying Firebase token: {e}")
        print(traceback.format_exc())
        return None 