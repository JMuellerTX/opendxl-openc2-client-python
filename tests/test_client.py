"""
Unit tests for the OpenC2 DXL client (no broker required): the DXL client
is replaced by a fake that records the requests and returns canned
responses.
"""

import json
import unittest

import openc2
from dxlclient.message import ErrorResponse, Request, Response
from dxlopenc2client import OpenC2Client


class FakeDxlClient(object):
    """Fake DxlClient answering every request with the configured payload"""

    def __init__(self, response_dict=None, error_message=None):
        self.response_dict = response_dict
        self.error_message = error_message
        self.requests = []

    def sync_request(self, request, timeout=None): # pylint: disable=unused-argument
        self.requests.append(request)
        if self.error_message:
            return ErrorResponse(request, error_code=0,
                                 error_message=self.error_message)
        response = Response(request)
        response.payload = json.dumps(self.response_dict).encode("utf-8")
        return response


class OpenC2ClientTest(unittest.TestCase):

    def setUp(self):
        self.command = openc2.v10.Command(
            action="query",
            target=openc2.v10.Features(features=["versions", "profiles"]))

    def test_send_command(self):
        dxl_client = FakeDxlClient({
            "status": 200,
            "results": {"versions": ["1.0"]}})
        client = OpenC2Client(dxl_client)
        response = client.send_command("/openc2/service/test", self.command)

        self.assertIsInstance(response, openc2.v10.Response)
        self.assertEqual(200, response.status)
        self.assertEqual(["1.0"], response.results["versions"])

        request = dxl_client.requests[0]
        self.assertIsInstance(request, Request)
        self.assertEqual("/openc2/service/test", request.destination_topic)
        self.assertIsInstance(request.payload, bytes)
        payload = json.loads(request.payload.decode("utf-8"))
        self.assertEqual("query", payload["action"])
        self.assertEqual({"features": ["versions", "profiles"]},
                         payload["target"])

    def test_error_response_raises(self):
        dxl_client = FakeDxlClient(error_message="unable to locate service")
        client = OpenC2Client(dxl_client)
        with self.assertRaises(Exception) as context:
            client.send_command("/openc2/service/test", self.command)
        self.assertIn("unable to locate service", str(context.exception))
