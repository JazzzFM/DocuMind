"""
API Authentication Tests
Tests for JWT token authentication endpoints and authorization.
"""
import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import json


class AuthenticationAPITestCase(TestCase):
    """Test JWT authentication endpoints."""
    
    def setUp(self):
        """Set up test client and user."""
        self.client = APIClient()
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.token_url = reverse('token_obtain_pair')
        self.refresh_url = reverse('token_refresh')
        
    def test_obtain_token_success(self):
        """Test successful JWT token generation."""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(self.token_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
        # Validate token structure
        access_token = response.data['access']
        refresh_token = response.data['refresh']
        self.assertIsInstance(access_token, str)
        self.assertIsInstance(refresh_token, str)
        self.assertTrue(len(access_token) > 50)  # JWT tokens are long
        self.assertTrue(len(refresh_token) > 50)
    
    def test_obtain_token_invalid_credentials(self):
        """Test token generation with invalid credentials."""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.token_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)
    
    def test_obtain_token_missing_credentials(self):
        """Test token generation with missing credentials."""
        data = {'username': 'testuser'}
        response = self.client.post(self.token_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
    
    def test_refresh_token_success(self):
        """Test successful token refresh."""
        # First get tokens
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        token_response = self.client.post(self.token_url, data, format='json')
        refresh_token = token_response.data['refresh']
        
        # Now refresh the token
        refresh_data = {'refresh': refresh_token}
        response = self.client.post(self.refresh_url, refresh_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        
        # New access token should be different
        new_access_token = response.data['access']
        original_access_token = token_response.data['access']
        self.assertNotEqual(new_access_token, original_access_token)
    
    def test_refresh_token_invalid(self):
        """Test token refresh with invalid refresh token."""
        data = {'refresh': 'invalid_refresh_token'}
        response = self.client.post(self.refresh_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', response.data)
    
    def test_protected_endpoint_without_token(self):
        """Test accessing protected endpoint without authentication."""
        # Try to access a protected endpoint (document processing)
        process_url = reverse('document_process')
        response = self.client.post(process_url, {}, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_protected_endpoint_with_valid_token(self):
        """Test accessing protected endpoint with valid JWT token."""
        # Get valid token
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        token_response = self.client.post(self.token_url, data, format='json')
        access_token = token_response.data['access']
        
        # Set authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Try to access system status (should work without file upload)
        status_url = reverse('system_status')
        response = self.client.get(status_url)
        
        # Should not be unauthorized (might be other errors due to missing components)
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_protected_endpoint_with_invalid_token(self):
        """Test accessing protected endpoint with invalid JWT token."""
        # Set invalid authorization header
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token_here')
        
        # Try to access protected endpoint
        status_url = reverse('system_status')
        response = self.client.get(status_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_token_expiration_behavior(self):
        """Test behavior when access token is expired."""
        # Note: This is a conceptual test - actual expiration testing
        # would require time manipulation or very short token lifetimes
        
        # Get tokens
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        token_response = self.client.post(self.token_url, data, format='json')
        
        # Verify we get both access and refresh tokens
        self.assertIn('access', token_response.data)
        self.assertIn('refresh', token_response.data)
        
        # In a real scenario, you would wait for token expiration
        # or modify settings to have very short token lifetime
        # For now, we just verify the refresh mechanism works
        refresh_data = {'refresh': token_response.data['refresh']}
        refresh_response = self.client.post(self.refresh_url, refresh_data, format='json')
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)


class APIPermissionsTestCase(TestCase):
    """Test API permissions and access control."""
    
    def setUp(self):
        """Set up test client and users."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='normaluser',
            email='user@example.com',
            password='userpass123'
        )
        self.admin_user = User.objects.create_superuser(
            username='adminuser',
            email='admin@example.com',
            password='adminpass123'
        )
        self.token_url = reverse('token_obtain_pair')
    
    def _get_user_token(self, username, password):
        """Helper method to get JWT token for user."""
        data = {'username': username, 'password': password}
        response = self.client.post(self.token_url, data, format='json')
        return response.data['access']
    
    def test_normal_user_access_to_endpoints(self):
        """Test normal user access to various endpoints."""
        token = self._get_user_token('normaluser', 'userpass123')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Test access to various endpoints
        endpoints = [
            ('system_status', 'get'),
            ('document_types', 'get'),
            ('statistics', 'get'),
        ]
        
        for endpoint_name, method in endpoints:
            url = reverse(endpoint_name)
            if method == 'get':
                response = self.client.get(url)
            elif method == 'post':
                response = self.client.post(url, {})
            
            # Should not be unauthorized (might have other errors due to missing deps)
            self.assertNotEqual(
                response.status_code, 
                status.HTTP_401_UNAUTHORIZED,
                f"User should have access to {endpoint_name}"
            )
    
    def test_rate_limiting_configuration(self):
        """Test that rate limiting is properly configured."""
        # This test verifies that rate limiting settings are in place
        # Actual rate limiting testing would require making many requests
        
        from django.conf import settings
        
        # Verify throttle settings exist
        rest_framework_settings = getattr(settings, 'REST_FRAMEWORK', {})
        self.assertIn('DEFAULT_THROTTLE_CLASSES', rest_framework_settings)
        self.assertIn('DEFAULT_THROTTLE_RATES', rest_framework_settings)
        
        # Verify throttle rates are configured
        throttle_rates = rest_framework_settings.get('DEFAULT_THROTTLE_RATES', {})
        self.assertIn('anon', throttle_rates)
        self.assertIn('user', throttle_rates)


@pytest.mark.django_db
class TestJWTTokenLifecycle:
    """Pytest-style tests for JWT token lifecycle."""
    
    def test_token_contains_user_information(self):
        """Test that JWT token contains expected user information."""
        from rest_framework_simplejwt.tokens import AccessToken
        from django.contrib.auth.models import User
        
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        
        token = AccessToken.for_user(user)
        
        # Verify token contains user ID
        self.assertEqual(token['user_id'], user.id)
        
        # Verify token type
        self.assertEqual(token['token_type'], 'access')
    
    def test_token_validation(self):
        """Test token validation logic."""
        from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
        from django.contrib.auth.models import User
        
        user = User.objects.create_user(username='testuser')
        
        # Create tokens
        access_token = AccessToken.for_user(user)
        refresh_token = RefreshToken.for_user(user)
        
        # Validate tokens
        self.assertIsNotNone(access_token)
        self.assertIsNotNone(refresh_token)
        
        # Test token string representation
        access_token_str = str(access_token)
        refresh_token_str = str(refresh_token)
        
        self.assertTrue(len(access_token_str) > 50)
        self.assertTrue(len(refresh_token_str) > 50)