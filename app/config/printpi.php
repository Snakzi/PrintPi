<?php

return [

    /*
    | Where the browser reaches the camera stream. On the Pi nginx proxies
    | ustreamer under /webcam/; on a dev machine point this at ustreamer itself.
    */
    'webcam_base' => env('PRINTPI_WEBCAM_BASE', '/webcam'),

    /*
    | Root helper that applies hostname and timezone on the Pi, allowed for
    | www-data through sudoers. Absent on dev machines, then changes are only stored.
    */
    'system_helper' => env('PRINTPI_SYSTEM_HELPER', '/usr/local/bin/printpi-system'),

    /*
    | Installed release version, alongside the app in the active release tree.
    */
    'version_file' => env('PRINTPI_VERSION_FILE', base_path('../VERSION')),

    /*
    | Installation home containing the current and previous release symlinks.
    */
    'home' => env('PRINTPI_HOME', '/opt/printpi'),

    /*
    | Static release host with a manifest for each update channel.
    */
    'update_url' => env('PRINTPI_UPDATE_URL', 'https://updates.194-164-58-152.sslip.io'),

    /*
    | Channels the update host publishes, the first one is the default. Stable
    | joins the list with the first stable release; until then every install
    | follows beta and a stored channel outside the list falls back to the first.
    */
    'update_channels' => ['beta'],

    /*
    | Progress of the detached update or rollback, written by the root helper.
    */
    'update_status_file' => env('PRINTPI_UPDATE_STATUS_FILE', '/run/printpi/update.json'),

    /*
    | Where the daemon writes the timelapse of every print (cover photo, GIF and
    | MP4 when ffmpeg exists) and where the app serves them from. The daemon
    | defaults to this same directory of the checkout it runs from.
    */
    'timelapse_dir' => env('PRINTPI_TIMELAPSE_DIR', storage_path('app/timelapse')),

    /*
    | Plugins: the built-in ones ship in the repository, plugins installed from git
    | are cloned into a directory the web app writes and the daemon reads.
    */
    'plugins' => [
        'builtin' => env('PRINTPI_BUILTIN_PLUGINS_DIR', dirname(__DIR__, 2).'/plugins'),
        'installed' => env('PRINTPI_PLUGINS_DIR', storage_path('app/plugins')),
    ],

    /*
    | The secret the kiosk browser on the Pi's touch screen signs in with over
    | loopback (GET /panel/login?token=…); the installer generates it. Empty
    | switches the endpoint off.
    */
    'panel_token' => env('PRINTPI_PANEL_TOKEN'),

];
