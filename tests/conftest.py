import os
import sys
import pytest
from dotenv import load_dotenv

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

@pytest.fixture(autouse=True)
def setup_test_env():
    """Fixture to set up test environment variables.
    The autouse=True means this will run automatically for every test.
    """
    # Store original environment
    original_env = dict(os.environ)
    
    # Load .env file if it exists
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
    
    # Set test environment variables
    os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', 'test_key')
    os.environ['SERPAPI_KEY'] = os.getenv('SERPAPI_KEY', 'test_key')
    os.environ['LANGSMITH_TRACING'] = os.getenv('LANGSMITH_TRACING', 'test_value')
    os.environ['LANGSMITH_ENDPOINT'] = os.getenv('LANGSMITH_ENDPOINT', 'test_value')
    os.environ['LANGSMITH_API_KEY'] = os.getenv('LANGSMITH_API_KEY', 'test_key')
    os.environ['LANGSMITH_PROJECT'] = os.getenv('LANGSMITH_PROJECT', 'test_value')
    os.environ['GOOGLE_MAPS_API_KEY'] = os.getenv('GOOGLE_MAPS_API_KEY', 'test_key')
    os.environ['QDRANT_API_KEY'] = os.getenv('QDRANT_API_KEY', 'test_key')
    os.environ['QDRANT_URL'] = os.getenv('QDRANT_URL', 'test_value')
    
    yield  # This is where the test runs
    
    # Restore original environment after test
    os.environ.clear()
    os.environ.update(original_env) 