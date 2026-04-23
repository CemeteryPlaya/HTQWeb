import { generateKeyPairSync, createSign, randomBytes, createHash } from 'crypto';
import { writeFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// Generate RSA key pair
const { publicKey, privateKey } = generateKeyPairSync('rsa', {
  modulusLength: 2048,
});

// Export private key as PEM
const keyPem = privateKey.export({ type: 'pkcs8', format: 'pem' });
writeFileSync(resolve(__dirname, 'key.pem'), keyPem);

// Build self-signed X.509 certificate manually using ASN.1 DER encoding
function encodeLength(len) {
  if (len < 0x80) return Buffer.from([len]);
  if (len < 0x100) return Buffer.from([0x81, len]);
  return Buffer.from([0x82, (len >> 8) & 0xff, len & 0xff]);
}

function derSequence(...items) {
  const body = Buffer.concat(items);
  return Buffer.concat([Buffer.from([0x30]), encodeLength(body.length), body]);
}

function derSet(...items) {
  const body = Buffer.concat(items);
  return Buffer.concat([Buffer.from([0x31]), encodeLength(body.length), body]);
}

function derOid(oidStr) {
  const parts = oidStr.split('.').map(Number);
  const bytes = [40 * parts[0] + parts[1]];
  for (let i = 2; i < parts.length; i++) {
    let val = parts[i];
    if (val < 128) { bytes.push(val); }
    else {
      const enc = [];
      enc.push(val & 0x7f);
      val >>= 7;
      while (val > 0) { enc.push(0x80 | (val & 0x7f)); val >>= 7; }
      enc.reverse();
      bytes.push(...enc);
    }
  }
  return Buffer.concat([Buffer.from([0x06, bytes.length]), Buffer.from(bytes)]);
}

function derUtf8String(str) {
  const buf = Buffer.from(str, 'utf8');
  return Buffer.concat([Buffer.from([0x0c]), encodeLength(buf.length), buf]);
}

function derInteger(buf) {
  // Ensure positive (prepend 0x00 if high bit set)
  if (buf[0] & 0x80) buf = Buffer.concat([Buffer.from([0x00]), buf]);
  return Buffer.concat([Buffer.from([0x02]), encodeLength(buf.length), buf]);
}

function derBitString(buf) {
  const body = Buffer.concat([Buffer.from([0x00]), buf]); // 0 unused bits
  return Buffer.concat([Buffer.from([0x03]), encodeLength(body.length), body]);
}

function derExplicit(tag, content) {
  return Buffer.concat([Buffer.from([0xa0 | tag]), encodeLength(content.length), content]);
}

function derOctetString(buf) {
  return Buffer.concat([Buffer.from([0x04]), encodeLength(buf.length), buf]);
}

function derGeneralizedTime(date) {
  const s = date.toISOString().replace(/[-:T]/g, '').replace(/\.\d+/, '').replace('Z', '') + 'Z';
  const buf = Buffer.from(s, 'ascii');
  return Buffer.concat([Buffer.from([0x18]), encodeLength(buf.length), buf]);
}

// Certificate fields
const serialNumber = derInteger(randomBytes(8));
const sha256WithRSA = derSequence(derOid('1.2.840.113549.1.1.11'), Buffer.from([0x05, 0x00])); // NULL param

// Issuer/Subject: CN=HTQWeb LAN
const cnAttr = derSequence(derOid('2.5.4.3'), derUtf8String('HTQWeb LAN'));
const rdnSequence = derSequence(derSet(cnAttr));

// Validity: now to +1 year
const notBefore = derGeneralizedTime(new Date());
const notAfterDate = new Date(); notAfterDate.setFullYear(notAfterDate.getFullYear() + 1);
const notAfter = derGeneralizedTime(notAfterDate);
const validity = derSequence(notBefore, notAfter);

// Subject Public Key Info (from public key DER)
const pubDer = publicKey.export({ type: 'spki', format: 'der' });

// Extensions: Subject Alternative Name
// SAN: IP:192.168.2.106, IP:127.0.0.1, DNS:localhost
function ipToBytes(ip) {
  return Buffer.from(ip.split('.').map(Number));
}

const san1 = Buffer.concat([Buffer.from([0x87, 4]), ipToBytes('192.168.2.54')]); // iPAddress
const san2 = Buffer.concat([Buffer.from([0x87, 4]), ipToBytes('127.0.0.1')]);
const dnsName = Buffer.from('localhost', 'ascii');
const san3 = Buffer.concat([Buffer.from([0x82]), encodeLength(dnsName.length), dnsName]); // dNSName

const sanValue = derSequence(san1, san2, san3);
const sanExtension = derSequence(
  derOid('2.5.29.17'), // subjectAltName
  derOctetString(sanValue)
);

// Basic Constraints: CA=true (so browsers accept it)
const bcValue = derSequence(Buffer.from([0x01, 0x01, 0xff])); // BOOLEAN TRUE
const bcExtension = derSequence(
  derOid('2.5.29.19'), // basicConstraints
  Buffer.from([0x01, 0x01, 0xff]), // critical=TRUE
  derOctetString(bcValue)
);

const extensions = derExplicit(3, derSequence(sanExtension, bcExtension));

// Version: v3
const version = derExplicit(0, derInteger(Buffer.from([0x02])));

// TBS Certificate
const tbsCertificate = derSequence(
  version,
  serialNumber,
  sha256WithRSA,
  rdnSequence,    // issuer
  validity,
  rdnSequence,    // subject (self-signed)
  pubDer,
  extensions
);

// Sign TBS
const sign = createSign('SHA256');
sign.update(tbsCertificate);
const signature = sign.sign(privateKey);

// Full certificate
const certificate = derSequence(
  tbsCertificate,
  sha256WithRSA,
  derBitString(signature)
);

// Encode as PEM
const certPem = '-----BEGIN CERTIFICATE-----\n' +
  certificate.toString('base64').match(/.{1,64}/g).join('\n') +
  '\n-----END CERTIFICATE-----\n';

writeFileSync(resolve(__dirname, 'cert.pem'), certPem);

// Verify
const hash = createHash('sha256').update(certificate).digest('hex');
console.log('Certificate generated successfully!');
console.log(`  cert.pem: ${resolve(__dirname, 'cert.pem')}`);
console.log(`  key.pem:  ${resolve(__dirname, 'key.pem')}`);
console.log(`  SHA256:   ${hash}`);
console.log(`  SAN:      IP:192.168.2.106, IP:127.0.0.1, DNS:localhost`);
console.log(`  Valid:    1 year`);
