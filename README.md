# Dolby Digital 5.1 para Decky / Dolby Digital 5.1 for Decky

*Plugin de Decky Loader para Steam Deck / A Decky Loader plugin for Steam Deck*

---

## Español

Plugin de Decky Loader para SteamOS que activa el perfil `hdmi-ac3.conf` de SteamOS. Hace que el codificador ALSA `a52` convierta el audio PCM multicanal en AC-3 (Dolby Digital) 5.1 en tiempo real por HDMI/DisplayPort.

Está pensado para una Steam Deck conectada a una TV, barra de sonido o receptor que acepte Dolby Digital pero no PCM 5.1. No crea canales físicos adicionales: hace que el receptor reciba un bitstream AC-3 5.1 compatible.

### Uso

No necesitas configurar nada de Linux a mano — el plugin se encarga de todo.

1. Activa el Modo Desarrollador en Decky (Menú rápido → pestaña de Decky → icono de engranaje → activar Modo Desarrollador).
2. En los ajustes de Desarrollador, usa "Instalar plugin desde ZIP" y elige el archivo descargado.
3. Abre el plugin desde la pestaña de Decky, conecta tu TV por HDMI (encendida) y pulsa el botón para activar el cambio automático de HDMI.
4. Reinicia tu Steam Deck una vez (solo hace falta la primera vez).
5. Listo — a partir de ahora cambia a 5.1 automáticamente al conectar el HDMI, y vuelve a los altavoces de la Deck al desconectarlo.

### Compatibilidad y límites

- Requiere SteamOS con `hdmi-ac3.conf` y el módulo ALSA `a52` incluidos. Si el sistema no los trae, el plugin instala automáticamente su propia copia del perfil en `~/.config/alsa-card-profile/`.
- Funciona con HDMI/DisplayPort; Bluetooth no transporta AC-3 5.1 de esta forma.
- Si no aparece un perfil AC-3, verifica que el receptor/TV esté encendido y conectado antes de activar el plugin.
- Las actualizaciones de SteamOS pueden cambiar el perfil interno del sistema. El plugin comprueba su presencia antes de aplicarlo y lo recrea si hiciera falta.

### Desarrollo

La interfaz se compila con `pnpm run build`; el resultado se guarda en `dist/`. El backend en Python usa la API de Decky para consultar `pactl`, crear el drop-in de WirePlumber y seleccionar el primer perfil `output:hdmi-ac3-surround` disponible.

---

## English

A Decky Loader plugin for SteamOS that activates SteamOS's `hdmi-ac3.conf` profile. It makes the ALSA `a52` encoder transcode multichannel PCM audio into real-time AC-3 (Dolby Digital) 5.1 over HDMI/DisplayPort.

It's designed for a Steam Deck connected to a TV, soundbar, or receiver that accepts Dolby Digital but not 5.1 PCM. It doesn't create extra physical channels — it makes the receiver receive a compatible AC-3 5.1 bitstream instead.

### Usage

You don't need to set up any Linux configuration by hand — the plugin takes care of everything.

1. Enable Developer Mode in Decky (Quick Access Menu → Decky tab → gear icon → toggle Developer Mode).
2. In Developer settings, use "Install Plugin from ZIP" and pick the downloaded file.
3. Open the plugin from the Decky tab, connect your TV via HDMI (powered on), and press the button to enable automatic HDMI switching.
4. Restart your Steam Deck once (only needed the first time).
5. Done — from now on it switches to 5.1 automatically when you plug in HDMI, and back to the Deck speakers when you unplug it.

### Compatibility and limits

- Requires a SteamOS build that ships `hdmi-ac3.conf` and the ALSA `a52` module. If the system doesn't have them, the plugin automatically installs its own copy of the profile under `~/.config/alsa-card-profile/`.
- Works over HDMI/DisplayPort; Bluetooth cannot carry AC-3 5.1 this way.
- If no AC-3 profile shows up, make sure the receiver/TV is powered on and connected before enabling the plugin.
- SteamOS updates can change the system's internal profile. The plugin checks for its presence before applying it and recreates it if needed.

### Development

The frontend is built with `pnpm run build`; output goes to `dist/`. The Python backend uses the Decky API to query `pactl`, create the WirePlumber drop-in, and pick the first available `output:hdmi-ac3-surround` profile.
