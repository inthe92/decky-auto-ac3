# Dolby Digital 5.1 para Decky

Plugin de Decky Loader para SteamOS que activa el perfil `hdmi-ac3.conf` de
SteamOS. Hace que el codificador ALSA a52 convierta el audio PCM multicanal en
AC-3 (Dolby Digital) 5.1 en tiempo real por HDMI/DisplayPort.

Está pensado para una Steam Deck conectada a una TV, barra o receptor que
acepte Dolby Digital pero no PCM 5.1. No crea canales físicos: hace que el
receptor reciba un bitstream AC-3 5.1 compatible.

## Uso

No necesitas configurar nada de Linux a mano — el plugin se encarga de todo.
Activa el Modo Desarrollador en Decky (Menú rápido → pestaña de Decky → icono de engranaje → activar Modo Desarrollador).
En los ajustes de Desarrollador, usa "Instalar plugin desde ZIP" y elige el archivo descargado.
Abre el plugin desde la pestaña de Decky, conecta tu TV por HDMI (encendida) y pulsa el botón para activar el cambio automático de HDMI.
Reinicia tu Steam Deck una vez (solo hace falta la primera vez).
Listo — a partir de ahora cambia a 5.1 automáticamente al conectar el HDMI, y vuelve a los altavoces de la Deck al desconectarlo.

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
