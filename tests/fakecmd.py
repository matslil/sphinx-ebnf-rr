#!/bin/sh

printf '%s ' java '-jar' /home/mats/bin/rr-2.0/rr.war "$@"
echo

exec java -jar /home/mats/bin/rr-2.0/rr.war "$@"
