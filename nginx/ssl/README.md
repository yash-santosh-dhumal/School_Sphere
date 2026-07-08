SSL certificates go here.

Place your SSL certificate files in this directory:
- fullchain.pem
- privkey.pem

To generate with Let's Encrypt:
  certbot certonly --standalone -d yourdomain.com

Then uncomment the HTTPS blocks in nginx/nginx.conf.
