# Yggdrasil Keys

Hardened, offline HeliBoard with the Yggdrasil theme. The app's source lives in the private repo
`Ozorhaar/yggdrasil-keys` (HeliBoard history + one Yggdrasil commit). This patch is that commit,
minus two binary files:

- `app/src/main/assets/fonts/yggdrasil_runic.ttf` = the launcher's `res/font/yggdrasil_runic.ttf`
  (sha256 5792d9956c13b0e245dd8e442b35f8b90b6540e573a3f6569238abbc42ff5ad3)
- `app/src/main/res/drawable-nodpi/ygg_keyboard_bg.png` = `phone-aod/yggdrasil-keyboard.png` here
  (sha256 cf209e511dd9a7f35f258724e176b7939477436518d5324e40108c5a3fc77b2e)
