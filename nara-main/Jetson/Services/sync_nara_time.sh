#!/bin/bash
echo "NARA: Iniciando sincronizacao de tempo..."
sleep 5

echo "NARA: Corrigindo DNS..."
rm -f /etc/resolv.conf
echo "nameserver 192.168.0.1" > /etc/resolv.conf
sleep 2

HTTP_DATE=$(curl -sI --connect-timeout 5 http://www.google.com | grep -i '^Date:' | sed 's/^[Dd]ate: //I' | tr -d '\r')

if [ -n "$HTTP_DATE" ]; then
    date -s "$HTTP_DATE"
    echo "NARA: Relogio sincronizado com sucesso via Google!"
    exit 0
fi

echo "NARA: Sem internet. Setando data de seguranca."
date -s "Wed Apr 29 12:00:00 -03 2026"
