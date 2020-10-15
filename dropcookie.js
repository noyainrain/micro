
        if (version < 3) {
            document.cookie = "auth_secret=; path=/; max-age=0";
            localStorage.microVersion = 3;
        }

        in go:
                this.api = new micro.WebApi({headers: this._data.user ? {Authorization: `Bearer ${this._data.user.auth_secret}`} : {}});

     _storeUser(user) {
        localStorage.microUser = JSON.stringify(user);
        // TODO where to set this; must be set whenever data.user is set, two places, here and on
        // first load
        this.api = new micro.WebApi({headers: this._data.user ? {Authorization: `Bearer ${this._data.user.auth_secret}`} : {}});
     }

in general.inc:
TODO update doc + examples, also deprecation note

in server endpoint prepare:
        auth = self.request.headers.get('Authorization')
        # TODO compatibility with cookies
        # TODO check header for errors BAD REQUEST
        auth_secret = auth.split()[1] if auth else self.get_cookie('auth_secret')
        print('GOT HEADER', auth, 'SECRET', auth_secret)
