from flask import jsonify
from werkzeug.http import HTTP_STATUS_CODES


def error_response(status_code, message=None):
    payload = {'error': HTTP_STATUS_CODES.get(status_code, 'Unknown error')}
    if message:
        payload['message'] = message
    response = jsonify(payload)
    # The jsonify() function returns a Flask Response object with a default
    # status code of 200, so after I create the response, I set the status
    # code to the correct one for the error.
    response.status_code = status_code
    return response


def bad_request(message):
    # Response for error 400
    return error_response(400, message)