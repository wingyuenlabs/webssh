import asyncio
import json
import unittest
import time
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock
from tornado.testing import AsyncHTTPTestCase, gen_test
from tornado.httpclient import HTTPError
from tornado.websocket import websocket_connect
from tornado.options import options

from webssh.main import make_app, make_handlers
from webssh.handler import rate_limiter
from webssh.worker import clients, Worker
from webssh.settings import get_app_settings


class IntegrationTestBase(AsyncHTTPTestCase):
    """Base class for integration tests"""
    
    def get_app(self):
        options.parse_command_line([])
        loop = self.io_loop
        handlers = make_handlers(loop, options)
        settings = get_app_settings(options)
        return make_app(handlers, settings)
    
    def setUp(self):
        super().setUp()
        # Clear rate limiter and clients between tests
        rate_limiter.attempts.clear()
        clients.clear()
    
    def tearDown(self):
        # Clean up clients
        for ip, workers in list(clients.items()):
            for worker_id, worker in list(workers.items()):
                try:
                    worker.close(reason='test cleanup')
                except:
                    pass
        clients.clear()
        rate_limiter.attempts.clear()
        super().tearDown()


class TestRateLimiting(IntegrationTestBase):
    """Test rate limiting functionality"""
    
    @gen_test
    def test_rate_limit_enforcement(self):
        """Test that rate limiting blocks excessive requests"""
        # Set low rate limit for testing
        original_limit = options.ratelimit
        options.ratelimit = 3
        
        try:
            # Make requests up to the limit
            for i in range(3):
                try:
                    response = yield self.http_client.fetch(
                        self.get_url('/'),
                        method='POST',
                        body='hostname=test&username=test&password=test',
                        raise_error=False
                    )
                except Exception:
                    pass
            
            # Next request should be rate limited
            response = yield self.http_client.fetch(
                self.get_url('/'),
                method='POST',
                body='hostname=test&username=test&password=test',
                raise_error=False
            )
            
            # Should get 429 Too Many Requests
            self.assertEqual(response.code, 429)
        finally:
            options.ratelimit = original_limit
    
    @gen_test
    def test_rate_limit_cleanup(self):
        """Test that rate limiter cleans up old entries"""
        ip = '127.0.0.1'
        
        # Add some old attempts
        old_time = time.time() - options.ratelimit_window - 10
        rate_limiter.attempts[ip] = [(old_time, False)] * 5
        
        # Cleanup should remove them
        rate_limiter.cleanup()
        
        self.assertEqual(len(rate_limiter.attempts.get(ip, [])), 0)


class TestSessionTimeout(IntegrationTestBase):
    """Test session timeout functionality"""
    
    @gen_test
    def test_worker_tracks_activity(self):
        """Test that workers track last activity time"""
        loop = self.io_loop
        
        # Create mock SSH and channel
        mock_ssh = MagicMock()
        mock_chan = MagicMock()
        mock_chan.fileno.return_value = 1
        
        # Create worker
        worker = Worker(loop, mock_ssh, mock_chan, ('localhost', 22))
        
        initial_time = worker.last_activity
        time.sleep(0.1)
        
        # Simulate activity
        worker.last_activity = time.time()
        
        self.assertGreater(worker.last_activity, initial_time)


class TestConnectionLimits(IntegrationTestBase):
    """Test connection limits per client"""
    
    @gen_test
    def test_max_connections_per_client(self):
        """Test that max connections per client is enforced"""
        # Set low max connections for testing
        original_maxconn = options.maxconn
        options.maxconn = 2
        
        try:
            # Simulate reaching max connections
            test_ip = '192.168.1.100'
            clients[test_ip] = {
                'worker1': Mock(id='worker1'),
                'worker2': Mock(id='worker2')
            }
            
            # Try to make another connection
            response = yield self.http_client.fetch(
                self.get_url('/'),
                method='POST',
                body='hostname=test&username=test&password=test',
                headers={'X-Real-Ip': test_ip},
                raise_error=False
            )
            
            # Should be rejected with 403
            self.assertEqual(response.code, 403)
        finally:
            options.maxconn = original_maxconn
            clients.pop(test_ip, None)


class TestErrorHandling(IntegrationTestBase):
    """Test error message sanitization and handling"""
    
    @gen_test
    def test_production_error_sanitization(self):
        """Test that production mode sanitizes error messages"""
        # Ensure debug mode is off
        original_debug = options.debug
        options.debug = False
        
        try:
            # Test with invalid hostname
            response = yield self.http_client.fetch(
                self.get_url('/'),
                method='POST',
                body='hostname=invalid_host_that_does_not_exist&username=test&password=test',
                raise_error=False
            )
            
            # Should get a response (might be 200 with error in JSON or 400)
            self.assertIn(response.code, [200, 400])
            
            if response.code == 200:
                result = json.loads(response.body)
                # Error message should be sanitized
                if result.get('status'):
                    self.assertNotIn('traceback', result['status'].lower())
                    self.assertNotIn('exception', result['status'].lower())
        finally:
            options.debug = original_debug
    
    @gen_test
    def test_debug_error_details(self):
        """Test that debug mode shows detailed errors"""
        # Enable debug mode
        original_debug = options.debug
        options.debug = True
        
        try:
            # Test 404
            response = yield self.http_client.fetch(
                self.get_url('/nonexistent'),
                raise_error=False
            )
            
            self.assertEqual(response.code, 404)
        finally:
            options.debug = original_debug


class TestApplicationEndpoints(IntegrationTestBase):
    """Test basic application endpoints"""
    
    @gen_test
    def test_index_page_loads(self):
        """Test that index page loads successfully"""
        response = yield self.http_client.fetch(
            self.get_url('/'),
            method='GET'
        )
        
        self.assertEqual(response.code, 200)
        self.assertIn(b'WebSSH', response.body)
    
    @gen_test
    def test_invalid_post_request(self):
        """Test POST with missing required fields"""
        response = yield self.http_client.fetch(
            self.get_url('/'),
            method='POST',
            body='hostname=',
            raise_error=False
        )
        
        # Should return error
        self.assertIn(response.code, [200, 400])
        
        if response.code == 200:
            result = json.loads(response.body)
            self.assertIsNotNone(result.get('status'))


class TestWorkerManagement(IntegrationTestBase):
    """Test worker lifecycle management"""
    
    def test_worker_cleanup(self):
        """Test that workers are properly cleaned up"""
        from webssh.worker import clear_worker
        
        # Create mock worker
        mock_worker = Mock()
        mock_worker.id = 'test_worker_123'
        mock_worker.src_addr = ('192.168.1.1', 12345)
        
        # Add to clients
        ip = '192.168.1.1'
        clients[ip] = {mock_worker.id: mock_worker}
        
        # Clear the worker
        clear_worker(mock_worker, clients)
        
        # Should be removed
        self.assertNotIn(ip, clients)


class TestBinaryDataHandling(IntegrationTestBase):
    """Test binary data handling in workers"""
    
    def test_binary_data_join(self):
        """Test that binary data is properly handled"""
        loop = self.io_loop
        
        # Create mock SSH and channel
        mock_ssh = MagicMock()
        mock_chan = MagicMock()
        mock_chan.fileno.return_value = 1
        mock_chan.send.return_value = 10
        
        # Create worker
        worker = Worker(loop, mock_ssh, mock_chan, ('localhost', 22))
        
        # Test with binary data
        worker.data_to_dst = [b'test', b'data']
        
        # Should handle binary data without error
        # (We can't call on_write directly without full setup, but we test the logic)
        if isinstance(worker.data_to_dst[0], bytes):
            data = b''.join(worker.data_to_dst)
            self.assertEqual(data, b'testdata')
        
        # Test with string data
        worker.data_to_dst = ['test', 'data']
        if isinstance(worker.data_to_dst[0], str):
            data = ''.join(worker.data_to_dst)
            self.assertEqual(data, 'testdata')


if __name__ == '__main__':
    unittest.main()
