<?php
//------------------------------------------------------------------------------
//  NetAlertX
//  Open Source Network Guard / WIFI & LAN intrusion detector
//
//  app_conf_encode.php - Side-effect-free helpers for serializing app.conf values
//------------------------------------------------------------------------------
#  Puche 2021 / 2022+ jokob             support@netalertx.com                GNU GPLv3
//------------------------------------------------------------------------------

/**
 * Encode a string for use inside a single-quoted Python literal in app.conf.
 * Doubles backslashes so they round-trip unchanged, and replaces ' with the
 * legacy {s-quote} placeholder that the backend converts back per use.
 */
function encode_python_string($val) {
  return str_replace(['\\', '\''], ['\\\\', '{s-quote}'], $val);
}
