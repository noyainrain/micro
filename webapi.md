Unfortunately this change requires some amount of refactoring:

* TODO refactor micro.APIError -> micro.webapi.WebAPIError
* TODO refactor micro.NetworkError -> micro.webapi.NetworkError
* TODO refactor ui.call("/api/foo") -> ui.call("foo")

Testing:

We could deliver a JSON file with karma and thus could at least test parsing a response and 404
error
BUT a neat echo test for passed args queries headers like in webapi.py is not possible and
delivireng static files to simulate an api is kind of hacky, so just don't test for now
(because api is used so often in the codebase it is has pretty good test coverage)
