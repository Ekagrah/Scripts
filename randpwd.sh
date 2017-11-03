#!/bin/bash

#echo "$(openssl rand -base64 12 | tr "/" "^" | tr "+" "$" | tr -d "=" | sed -E 's/([[:alnum:]$^]{4})([[:alnum:]$^]{4})([[:alnum:]$^]{4})([[:alnum:]$^]{4})/\[\1-\2-\3-\4\]/' )"

passumod="$(openssl rand -base64 12 | tr "/" "^" | tr "+" "$" | tr -d "=" )"
passmod="$(echo "${passumod}" | sed -E 's/([[:alnum:]$^]{4})([[:alnum:]$^]{4})([[:alnum:]$^]{4})([[:alnum:]$^]{4})/\[\1-\2-\3-\4\]/' )"

echo "${passumod}"
echo "${passmod}"

exit 0
