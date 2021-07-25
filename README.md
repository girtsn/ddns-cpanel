# ddns-cpanel
DDNS implementation for cPanel in php and python
cPanel has their own implementation now but it has to be configured by the hosting provider which some of them (you, NameCheap), are not willing to do.

Important note - like all my "development", patched together from the work of others (all credits and copyrights of those pieces of code are theirs), namely
* https://github.com/badjware/certbot-dns-cpanel - the Python setup for interacting with Cpanel
* https://github.com/kbabioch/php-ddns

features:
* response codes +/- according to the proprietary protocols described e.g. here:
* https://help.dyn.com/remote-access-api/return-codes/
* supports both http and https (as unfortunately the nice folks @ DD-WRT are slow to update inadyn)
* will not update record if the update details are the same
* quite flexible on authentication, by http basic or by supplying via URL
* logging at both frontend and backend sides

Just need to put the files in a hosting solution with php and python support,
make configuration files out of the provided TEMPLATEs
and test it, then go time!
