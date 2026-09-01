# Missing intermediate certificates

Not trust anchors. Every certificate here is an *intermediate* that a source's own server
should send and does not. The chain still has to terminate at a root in the system store,
so nothing here weakens verification; it only supplies a link the server omitted.

Browsers hide this class of misconfiguration by fetching the missing intermediate from the
leaf certificate's Authority Information Access extension. Python does not do AIA
fetching, so the same site that loads fine in Chrome fails in a collector with
`unable to get local issuer certificate`.

| File | Needed by | Why |
|---|---|---|
| `globalsign-gcc-r46-ov-tls-ca-2025.pem` | `finance.karnataka.gov.in` | The site serves a leaf issued by *GlobalSign GCC R46 OV TLS CA 2025* and then attaches *GlobalSign RSA OV SSL CA 2018*, which signs nothing in the chain. Fetched from the AIA URL in the leaf: `http://secure.globalsign.com/cacert/gsgccr46ovtlsca2025.crt`. Issued by *GlobalSign Root R46*, which is in the system store. Expires 2029-06-23. |

To refresh one, read the AIA URL out of the live leaf and convert:

```sh
openssl s_client -connect <host>:443 -servername <host> </dev/null 2>/dev/null \
  | openssl x509 -noout -text | grep -A1 'Authority Information Access'
curl -sS -o i.crt <the CA Issuers URL> && openssl x509 -inform DER -in i.crt -out i.pem
```
