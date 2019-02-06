Investigation:

* Safari: fresh cookie + user
* PWA: fresh cookie + user
* Then (often after interacting in Safari again) old Safari cookie creeps into PWA
  where localStorage.user is (correctly) still PWA user
* GET /users/abc will then get a user without auth_secret
* Cookie gets set to auth_secret=undefined
* All POST requests now fail because we are not authenticated at all

* It almost seems as if the sent cookie is somehow cached for a POST request...
