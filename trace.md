  Application.authenticate()
  "HGET" "auth_secret_map" "ineymhzmhqdvqymi"
! "LRANGE" "users" "0" "-1" => SMEMBER / GET
  "GET" "User:pxyfehnnoewiinyj"

  Application.activity
  "GET" "Activity"

  Activity.json()
  "GET" "Settings"
  "LRANGE" "Activity.items" "0" "99"
! "GET" "Event:pdfowgdawwmpgtem" => MGET
! "GET" "Event:ikccvghwerzsfzbo"
! "GET" "Event:jiqhwxbhbeeslctu"

  Event.json():
    "GET" "List:apdeavzjpgacmbeu"
    List.json():
!     (GET User) => do not include authors
!     User.json():
!       "ZCARD" "User:pxyfehnnoewiinyj.lists"
      "ZCARD" "List:apdeavzjpgacmbeu.owners"
      "ZSCORE" "List:apdeavzjpgacmbeu.owners" "User:pxyfehnnoewiinyj"
      "LLEN" "List:apdeavzjpgacmbeu.items"
!   "LRANGE" "users" "0" "-1" => SMEMBER
    (GET User)
    User.json():
      "ZCARD" "User:pxyfehnnoewiinyj.lists"
