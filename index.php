<?php

/*
 * Copyright (c) 2015, 2016 Karol Babioch <karol@babioch.de>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

require 'ddns_config.php';

error_reporting(E_ALL|E_STRICT);

// define('HTTP_MOVED_PERMANENTLY', 301);

define('TTL_MIN', 30);
define('TTL_MAX', 86400);

// Check if invoked over HTTPS, redirect otherwise
//if (!isset($_SERVER['HTTPS']) || $_SERVER['HTTPS'] != 'on') {
//     header('Location: ' . $_SERVER['SERVER_NAME'], true, HTTP_MOVED_PERMANENTLY);
//     exit;
//}

// $c = print_r($_SERVER, true);
// file_put_contents('debug', $c, FILE_APPEND);

$date = new DateTime("now", new DateTimeZone($confTimeZone) );
$outdate = $date->format('Y-m-d H:i:s');

if (!isset($confUser) || !isset($confPass)) {
    echo 'badconf';
    file_put_contents('ddns-php.log', $outdate . ' ERROR - incorrect configuration, agent=' . $_SERVER['HTTP_USER_AGENT'] . "\n", FILE_APPEND );
    http_response_code(503);
    exit;
}

// Check for credentials via HTTP Basic Auth
if (isset($_SERVER['PHP_AUTH_USER'])) {

    $username = $_SERVER['PHP_AUTH_USER'];
    $password = $_SERVER['PHP_AUTH_PW'];

// Check for user crendentials via GET
} elseif (isset($_GET['username']) && isset($_GET['pass'])) {

    $username = $_GET['username'];
    $password = $_GET['pass'];

// No credentials provided
} else {

    // Ask for credentials via HTTP Basic Auth
    header('WWW-Authenticate: Basic realm="TODO"');
    header('HTTP/1.0 401 Unauthorized');
    echo 'badauth';
    file_put_contents('ddns-php.log', $outdate . ' ERROR - bad authentication, agent=' . $_SERVER['HTTP_USER_AGENT'] . "\n", FILE_APPEND );
    http_response_code(403);
    exit;

}
 
// Default TTL to 30 if not explicetely set
$ttl = (int) ($_GET['ttl'] ?? 30);

if ($ttl < TTL_MIN) {

    $ttl = TTL_MIN;

} elseif ($ttl > TTL_MAX) {

    $ttl = TTL_MAX;

}

if (isset($_GET['hostname'])) {

    // TODO: Filter / validate input
    $hostname = $_GET['hostname'];

} else {

    echo 'nxdomain';
    file_put_contents('ddns-php.log', $outdate . ' ERROR - no hostname, agent=' . $_SERVER['HTTP_USER_AGENT'] . "\n", FILE_APPEND);
    http_response_code(403);
    exit;

}

$domain = trim(get_domain($hostname));
$record = trim(get_record($hostname, $domain));

if (strlen($domain)>3 && strlen($record)>0 && strpos($domain, '.') !== false  && $username === $confUser &&  $password === $confPass) {

} else {

   echo 'badauth or bad hostname';
   file_put_contents('ddns-php.log', $outdate . ' ERROR - bad credentials or hostname, agent=' . $_SERVER['HTTP_USER_AGENT'] . ' hostname=' . $hostname . "\n", FILE_APPEND);
   http_response_code(403);
   exit;

}

if (isset($_GET['myip'])) {

    // TODO: Filter / validate
    $myip = $_GET['myip'];

} elseif (isset($_SERVER['REMOTE_ADDR'])) {

    // TODO myip() function
    $myip = $_SERVER['REMOTE_ADDR'];

} else {

    echo 'badip';
    file_put_contents('ddns-php.log', $outdate . ' ERROR - bad ip, agent=' . $_SERVER['HTTP_USER_AGENT'] . ' record=' . $record . ' ip=' . $myip . "\n", FILE_APPEND);
    http_response_code(404);
    exit;

}

// TODO: Logic for type vs IP (i.e. AAAA vs 192.168.0.1)
if (isset($_GET['type']) && ($_GET['type'] === 'A' || $_GET['type'] === 'AAAA')) {

    // TODO: Filter
    $type = $_GET['type'];

// Determine type by IP
} elseif(filter_var($myip, FILTER_VALIDATE_IP, FILTER_FLAG_IPV4)) {    

    $type = 'A';

} elseif (filter_var($myip, FILTER_VALIDATE_IP, FILTER_FLAG_IPV6)) {

    $type = 'AAAA';

} else {

   echo 'badtype';
   file_put_contents('ddns-php.log', $outdate . ' ERROR - bad record_type for agent=' . $_SERVER['HTTP_USER_AGENT'] . ' record=' . $record . ' ip=' . $myip . "\n", FILE_APPEND);
   http_response_code(404);
   exit;

}

    $proto = isset($_SERVER['HTTPS'] ) ? 'https' : 'http';
    $message = exec('python ' . getcwd() . '/ddns.py --domain=' . $domain . ' --record_name=' . $record . ' --ip=' . $myip . ' --record_type=' . $type . ' --record_ttl=' . $ttl . ' 2>&1');
    echo($message);
    if (substr($message, 0, 4) === 'good' || substr($message, 0, 5) === 'nochg') {
	file_put_contents('ddns-php.log', $outdate . ' - INFO - good ip update for proto=' . $proto . ' agent=' . $_SERVER['HTTP_USER_AGENT'] . ' record=' . $record . ' ip=' . $myip . "\n", FILE_APPEND);
	http_response_code(200);
    } else {
        file_put_contents('ddns-php.log', $outdate . ' - ERROR - failure from running python proto=' . $proto . ' agent=' . $_SERVER['HTTP_USER_AGENT'] . ' record=' . $record . ' ip=' . $myip . ' msg=' . $message . "\n", FILE_APPEND);
        http_response_code(500);
    }
    

function get_domain($host){
  $myhost = strtolower(trim($host));
  $count = substr_count($myhost, '.');
  if($count === 2){
    if(strlen(explode('.', $myhost)[1]) > 3) $myhost = explode('.', $myhost, 2)[1];
  } else if($count > 2){
    $myhost = get_domain(explode('.', $myhost, 2)[1]);
  }
  return $myhost;
}

function get_record($host, $domain){
  $myhost = strtolower(trim($host));
  $myrecord = $myhost .= '.';
  return $myrecord;
}
