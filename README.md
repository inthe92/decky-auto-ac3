# Dolby Digital 5.1 para Decky

Plugin de Decky Loader para SteamOS que activa el perfil `hdmi-ac3.conf` de
SteamOS. Hace que el codificador ALSA a52 convierta el audio PCM multicanal en
AC-3 (Dolby Digital) 5.1 en tiempo real por HDMI/DisplayPort.

Está pensado para una Steam Deck conectada a una TV, barra o receptor que
acepte Dolby Digital pero no PCM 5.1. No crea canales físicos: hace que el
receptor reciba un bitstream AC-3 5.1 compatible.

## Uso

1. Instala el plugin en Decky Loader como plugin local (la carpeta debe incluir
   `dist/index.js`).
2. Conecta el HDMI y abre **Dolby Digital 5.1** desde el menú de Decky.
3. Pulsa **Activar transcodificación Dolby Digital 5.1**.
4. Reproduce audio; la pantalla o el receptor debe indicar `Dolby Digital`.

El botón **Restaurar audio normal** elimina solamente el archivo de usuario
`~/.config/wireplumber/wireplumber.conf.d/99-decky-dolby-digital.conf` y
reinicia WirePlumber. No modifica archivos de SteamOS ni instala paquetes.

## Compatibilidad y límites

- Requiere SteamOS con `hdmi-ac3.conf` y el módulo ALSA `a52` incluidos.
- Funciona con HDMI/DisplayPort; Bluetooth no transporta AC-3 5.1 así.
- Si no aparece un perfil AC-3, verifica que el receptor/TV esté encendido y
  conectado antes de activar el perfil.
- Las actualizaciones de SteamOS pueden cambiar el perfil interno. El plugin
  comprueba su presencia antes de aplicarlo.

## Desarrollo

La interfaz se compila con `pnpm run build`; el resultado se guarda en `dist/`.
El backend Python usa el API de Decky para consultar `pactl`, crear el drop-in
de WirePlumber y seleccionar el primer perfil `output:hdmi-ac3-surround`
disponible.
