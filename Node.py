import ecdsa

private_key = None
public_key = None

def generateCryptoKeys():
    private_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
    public_key = private_key.get_verifying_key()
    public_key = public_key.to_string().hex()
    private_key = private_key.to_pem()

    print(public_key, private_key)

def signPayload(payload):
    sig = sk.sign(payload)  
    print(vk_string.hex(), '\n', sig.hex())
    vk.verify(sig, b"message")

message = "message"
#
vk = sk.get_verifying_key()
vk_string = vk.to_string()
sig = sk.sign(b"message")
print(vk_string.hex(), '\n', sig.hex())
vk.verify(sig, b"message") # True

generateCryptoKeys()
