#!/usr/bin/python3.7
import os
import subprocess
import sys
import time
import signal
import telnetlib
import socket
import urllib.parse
import sys
import importlib
import concurrent.futures
from os.path import splitext

localhost = '127.0.0.1'

"""
Compares proxy response body to direct response

Returns:
  A boolean indicating whether they both match
"""
def verify_correct_response(port):
  url = 'http://info.cern.ch/'
  proxy_data = get_through_proxy(int(port), url)
  direct_data = get_direct(url)
  return proxy_data and (proxy_data == direct_data)

"""
Compares time taken to perform a set of requests serially and in parallel

Returns:
  A boolean representing whether all requests succeeded 
  Speedup ratio gained by parellelizing (serial time / parallel time) 
"""
def test_concurrency(proxy_bin, pid, port):
  urls = ['http://apache.org/', 'http://www.ox.ac.uk/', 'http://www.ucla.edu', \
   'http://www.bu.edu', 'http://www.mit.edu/', 'http://info.cern.ch/', \
   'http://www.foxnews.com/', 'http://www.cnn.com/', 'http://europe.wsj.com/', \
   'http://www.bbc.co.uk/']  

  try:
    serial_port = int(port) + 1
    serial_pid = start_proxy(proxy_bin, serial_port)
  
    (serial_success, serial_elapsed) = serial_proxy(serial_port, urls);
    
    parallel_port = int(port) + 2

    parallel_pid = start_proxy(proxy_bin, parallel_port)
    
    (parallel_success, parallel_elapsed) = parallel_proxy(parallel_port, urls);
    
  finally:    
    terminate(serial_pid)
    terminate(parallel_pid)
  
  return ((serial_success and parallel_success), serial_elapsed / parallel_elapsed)

"""
Compares time taken by a cache hit and miss of the same page

Returns:
  A boolean representing whether cache results are correct
  Speedup ratio gained by caching (miss time / hit time) 
"""
def test_caching(port):
  
  start = time.time()
  proxy_data = get_through_proxy(int(port), 'http://www.mit.edu/')
  elapsed = time.time() - start
  
  start = time.time()
  proxy_data_cached = get_through_proxy(int(port), 'http://www.mit.edu/')
  elapsed_cached = time.time() - start
  
  return ((proxy_data == proxy_data_cached), elapsed / elapsed_cached)

"""
Runs request parsing tests (the ones included in the assignment skeleton)

Returns:
  A list of strings indicating the result of each test
"""
def run_parsing_tests(proxy_filename):
  try:
    module = importlib.import_module(splitext(proxy_filename)[0])
    result = []
    result.append(simple_http_validation_test_cases(module))
    result.append(simple_http_parsing_test_cases(module))
    return result
  except:
    return ["Failed to run tests: " + str(sys.exc_info()[0])]

def main():
  proxy_bin = sys.argv[1]
  port = sys.argv[2]
  
  proxy_pid = start_proxy(proxy_bin, port)
 
  try:
    print("Running parsing tests: ")
    print(run_parsing_tests(proxy_bin))
    
    print("Verifying response correctness: ")
    print(verify_correct_response(port))
    
    print("Running concurrency tests: ")
    print(test_concurrency(proxy_bin, proxy_pid, port))
    
    print("Running caching test: ")
    print(test_caching(port))
    
  finally:
    terminate(proxy_pid)



#######################################
# Helper functions
#######################################  

def terminate(pid):
  if is_process_alive(pid):
    os.kill(pid, signal.SIGINT)
    time.sleep (3)
    os.kill(pid, signal.SIGKILL)
    try:
      os.waitpid(pid, 0)
    except OSError:
      pass

def is_process_alive(pid):
  try:
    os.kill(pid, 0)
    return True
  except OSError:
    return False

def restart_proxy(proxy_bin, pid, port):
  terminate(pid)
  time.sleep(5)
  devnull = open(os.devnull, 'w')
  proxy_process = subprocess.Popen(["python3.7", proxy_bin, str(port)], stdout=devnull, stderr=devnull) 
     
def start_proxy(proxy_bin, port):
  devnull = open(os.devnull, 'w')
  proxy_process = subprocess.Popen(["python3.7", proxy_bin, str(port)], stdout=devnull, stderr=devnull) 
  proxy_pid = proxy_process.pid
  
  time.sleep(2)
  return proxy_pid
  
def get_through_proxy(proxy_port, url):
  return http_exchange(localhost, int(proxy_port), url)
  
def get_direct(url):
  return http_exchange(urllib.parse.urlparse (url).netloc, int(80), url)

def http_exchange(host, port, url):
  try:
    data = 'GET %s HTTP/1.0\r\n\r\n' % url;
    conn = telnetlib.Telnet()
    conn.open(host, port, timeout=10)
    conn.write(data.encode())
    data = conn.read_all().decode()
    conn.close ();
    return data
  except socket.error:
    print('Socket error while attempting to talk to proxy: %s port %s'  % (host, port));

def parallel_proxy(port, urls):
  start = time.time()
  success = 0
  with concurrent.futures.ThreadPoolExecutor(max_workers=len(urls)) as executor:
    future_to_url = [executor.submit(get_through_proxy, port, url) for url in urls]
    for future in concurrent.futures.as_completed(future_to_url):
      try:
        data = future.result()
        if data.find("HTTP") >= 0:
          success = success + 1
      except Exception as exc:
        print('%r generated an exception: %s' % ("", exc))
  return (success == len(urls), time.time() - start)

def serial_proxy(port, urls):
  start = time.time()
  success = 0
  for url in urls:
    data = get_through_proxy(port, url)
    if data.find("HTTP") >= 0:
      success = success + 1
  return (success == len(urls), time.time() - start)

def simple_http_parsing_test_cases(module):
    result_list = []

    client_addr = ("127.0.0.1", 9877)
    #######################################
    #######################################
    case = "Parse HTTP method."

    req_str = "GET / HTTP/1.0\r\nHost: www.google.com\r\n\r\n"
    parsed = module.parse_http_request(client_addr, req_str)

    actual_value = parsed.method
    correct_value = "GET"
    append_result(result_list, case, correct_value, actual_value)

    #######################################
    case = "Parse headers."

    # "Host: google.com" header is added to the request.
    # note that the ":" is removed.
    actual_value = parsed.headers[0]        # note: headers is a list of lists
    correct_value = ["Host", "www.google.com"]
    append_result(result_list, case, correct_value, actual_value)
    #######################################
    case = "Parse HTTP request path."

    correct_value = "/"
    actual_value = parsed.requested_path
    append_result(result_list, case, correct_value, actual_value)

    #######################################
    case = "Add Default value of the port if it doesn't exist in the request."

    correct_value = str(80)
    actual_value = str(parsed.requested_port)
    append_result(result_list, case, correct_value, actual_value)
    #######################################
    case = "Add requested host field."

    actual_value = parsed.requested_host
    correct_value = "www.google.com"
    append_result(result_list, case, correct_value, actual_value)

    #######################################
    #######################################

    case = "Convert full URL in request to relative path."

    actual_value = parsed.requested_path
    correct_value = "/"
    append_result(result_list, case, correct_value, actual_value)

    #######################################
    case = "Add host header if a full HTTP path is used in request."

    actual_value = parsed.headers[0]
    correct_value = ["Host", "www.google.com"]
    append_result(result_list, case, correct_value, actual_value)

    #######################################
    #######################################
    case = "Parse HTTP headers"

    req_str = "GET / HTTP/1.0\r\nHost: www.google.com\r\nAccept: application/json\r\n\r\n"
    parsed = module.parse_http_request(client_addr, req_str)

    actual_value = str(len(parsed.headers))
    correct_value = str(2)
    append_result(result_list, case, correct_value, actual_value)

    #######################################
    #######################################
    case = "convert HttpRequestInfo to a the corresponding HTTP request"
    # A request to www.google.com/ , note adding the ":" to headers
    # "Host" header comes first
    headers = [["Host", "www.google.com"], ["Accept", "application/json"]]
    req = module.HttpRequestInfo(client_addr, "GET",
                          "www.google.com", 80, "/", headers)

    http_string = "GET / HTTP/1.0\r\nHost: www.google.com\r\n"
    http_string += "Accept: application/json\r\n\r\n"

    correct_value = http_string
    actual_value = req.to_http_string()
    append_result(result_list, case, correct_value, actual_value)
    return result_list

def simple_http_validation_test_cases(module):
    result_list = []
   
    case = "Parse a valid HTTP request."
    req_str = "GET / HTTP/1.0\r\nHost: www.google.com\r\n\r\n"

    actual_value = module.check_http_request_validity(req_str)
    correct_value = module.HttpRequestState.GOOD
    append_result(result_list, case, correct_value, actual_value)
    #######################################
    #######################################

    case = "Parse an invalid HTTP request (invalid method)"
    req_str = "GOAT / HTTP/1.0\r\nHost: www.google.com\r\n\r\n"

    actual_value = module.check_http_request_validity(req_str)
    correct_value = module.HttpRequestState.INVALID_INPUT
    append_result(result_list, case, correct_value, actual_value)

    #######################################
    #######################################

    case = "Parse an invalid HTTP request (not-supported method)"
    req_str = "HEAD / HTTP/1.0\r\nHost: www.google.com\r\n\r\n"

    actual_value = module.check_http_request_validity(req_str)
    correct_value = module.HttpRequestState.NOT_SUPPORTED
    append_result(result_list, case, correct_value, actual_value)

    #######################################
    #######################################

    case = "Parse an invalid HTTP request (relative path with no host header)"
    req_str = "HEAD / HTTP/1.0\r\n\r\n"

    actual_value = module.check_http_request_validity(req_str)
    correct_value = module.HttpRequestState.INVALID_INPUT
    append_result(result_list, case, correct_value, actual_value)

    #######################################
    #######################################
    case = "Parse an invalid HTTP request (bad header [no colon, no value])"
    req_str = "HEAD www.google.com HTTP/1.0\r\nAccept \r\n"

    actual_value = module.check_http_request_validity(req_str)
    correct_value = module.HttpRequestState.INVALID_INPUT
    append_result(result_list, case, correct_value, actual_value)

    #######################################
    #######################################
    case = "Parse an invalid HTTP request (no HTTP version)"
    req_str = "HEAD / \r\nHost: www.google.com\r\n\r\n"

    actual_value = module.check_http_request_validity(req_str)
    correct_value = module.HttpRequestState.INVALID_INPUT
    append_result(result_list, case, correct_value, actual_value)

    #######################################
    #######################################
    case = "GET request with full URL in path returns GOOD"
    req_str = "GET http://google.com/ HTTP/1.0\r\n"

    actual_value = module.check_http_request_validity(req_str)
    correct_value = module.HttpRequestState.GOOD
    append_result(result_list, case, correct_value, actual_value)
    #######################################
    #######################################

    case = "GET request with relative path and host header returns GOOD"
    req_str = "GET / HTTP/1.0\r\nHost: google.com\r\n\r\n"

    actual_value = module.check_http_request_validity(req_str)
    correct_value = module.HttpRequestState.GOOD
    append_result(result_list, case, correct_value, actual_value)

    #######################################
    #######################################

    case = "Relative path without host header returns INVALID_INPUT"
    req_str = "GET / HTTP/1.0\r\n\r\n"

    actual_value = module.check_http_request_validity(req_str)
    correct_value = module.HttpRequestState.INVALID_INPUT
    append_result(result_list, case, correct_value, actual_value)
    return result_list
    
def lineno():
    return sys._getframe().f_back.f_lineno

def append_result(result_list, test_case, correct_value, actual_value):
  if correct_value == actual_value:
    result_list.append(f"[SUCCESS] {test_case}")
  else:
    result_list.append(f"[FAIL][Line {lineno()}] [failed] {test_case} Expected ( %s ) got ( %s )" % (correct_value, actual_value))

if __name__ == '__main__':
  main()
