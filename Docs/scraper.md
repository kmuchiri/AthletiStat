# Scraper Doc

Disable insecure warnings by default

## Requests
Getting a webpage
One of the methods from the requests module is called get. Get uses a single parameter which is a string of the URL of the webpage that you are trying to retrieve. It create a HTTP requests, sends it to a server, receives a reply and returns the reply as an object of the class Response.

```python
response = requests.get("https://api.github.com/events")
```

A Sessions object:
[sessions](https://requests.readthedocs.io/en/latest/user/advanced/)

## Urllib3
Using Retry
[retry](https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html)


