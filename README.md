# Linux fresh point

A Linux package-management application with a GTK 4 desktop interface and an interactive terminal interface for servers and SSH sessions. Review installed software, remove selected packages, and manage package-list restore points while keeping installed updates.

**Status:** experimental. APT inventory and previews have been tested on Debian 13. Pacman, Portage, DNF and Zypper adapters are implemented, but have not been validated on their native distributions.

## Interface preview

### Installed applications

![Installed applications](screenshots/01-installed-applications.png)

### All packages

![All packages](screenshots/02-all-packages.png)

### Restore points

![Restore points](screenshots/03-restore-points.png)

### About

![About Linux fresh point](screenshots/04-about.png)

## What it does

- Detects supported Linux distributions and their native package manager.
- Selects the desktop or terminal interface from the session environment, with `--tui` available to force terminal mode.
- Checks runtime libraries at startup and installs missing library packages through the host's native package manager.
- Lists installed packages and desktop applications owned by those packages.
- Supports selecting one or several packages for removal.
- Previews changes before requesting administrator authorization.
- Saves and deletes restore points containing package lists, not file backups.
- Uses a saved package list to identify later additions while retaining required dependencies and protected system packages.
- Keeps installed package versions rather than downgrading to versions recorded in a point.
- Records package-removal results in local logs.
- Offers English (default), Lithuanian, Russian, Simplified Chinese and Italian language preferences; some terminal prompts remain in English.
- Includes a portable source launcher, settings menu and license information.

## What “restore” means

A restore point records the packages present when you create it. It is **not** a filesystem snapshot, factory image or backup.

The application does not automatically know a distribution's original installation manifest or verify whether every installed update came from an official repository. It does not reinstall missing packages, restore settings or deleted files, or automatically repair a damaged package database. Flatpak, Snap, AppImage and manually installed software are outside its package-management scope.

Package removal scripts may delete service data. Configuration handling depends on the native package manager; there is no general option to preserve all configuration files. Review every removal plan and keep separate backups of important data.

## Package manager support

| Manager | Distribution families | Execution |
|---|---|---|
| APT | Debian, Ubuntu and derivatives | Integrated preview and privileged execution |
| Pacman | Arch and derivatives | Native confirmation in a terminal |
| Portage | Gentoo | Targeted dependency-aware `emerge --depclean --ask` |
| DNF | Fedora and RHEL derivatives | Native confirmation, with an RPM dependency preflight |
| Zypper | openSUSE and SLES | Native confirmation, with an RPM dependency preflight |

Unknown distributions and OSTree-based atomic systems are rejected. This is not universal support for every Linux distribution.

## Requirements

- Python 3 at `/usr/bin/python3`.
- The host's supported native package manager.
- `python3-apt` for APT; the Python Portage module for Gentoo; `pacman-conf` for Arch; `rpm` for RPM systems.
- Desktop mode: PyGObject, GTK 4 and GdkPixbuf introspection libraries; `pkexec` and a desktop PolicyKit authentication agent for removal.
- Non-APT removal from desktop mode: GNOME Terminal, Konsole, Xfce Terminal, MATE Terminal or xterm.
- Terminal mode: Python's `curses` module and an interactive terminal. Regular users need `sudo` or `doas` for privileged operations; root does not. GTK and a graphical terminal emulator are not required.

On startup, the launchers check the Python package-manager libraries and, in desktop mode, the GTK libraries. Missing library packages are installed through the native package manager, then checked again before launch. Installation may require network access and administrator authorization; root runs the installer directly. Terminal mode skips the GTK checks. Python itself, the native package manager, curses, and authorization tools must already be available. Run the GUI as your regular user, not with `sudo`; the TUI also supports root.

## Run

Download or clone the repository, then run from its directory:

```sh
./start
```

Git records the launchers as executable, so a fresh Linux Git checkout should run `./start` directly. If a ZIP extraction or file copy loses executable permissions, use `sh start` (no `chmod` needed), or run `chmod +x start` once. A script cannot change its own execute permission before the operating system allows it to run.

Startup selects GTK when `DISPLAY` or `WAYLAND_DISPLAY` identifies a graphical session, and the terminal interface when both are absent. `--tui` always selects terminal mode. In the terminal main menu and language menu, use the up/down arrows and Enter; number keys remain optional shortcuts.

On a server or another system without a graphical session, `./start` automatically opens the terminal interface. You can select it explicitly from any terminal:

```sh
./start --tui
```

The terminal interface mirrors the installed-applications, all-packages, restore-points, language and help views. Use the arrow keys to navigate, `Space` to select packages and `P` to preview a cleanup. It works over SSH when a terminal is allocated (for example, `ssh -t host`). You can run it as a regular user or as root. Regular users authorize removal through `sudo` or `doas`; root runs the backend directly. Both paths require reviewing and confirming a removal plan. Settings and restore points belong to the account running the application (or the portable data directory in portable mode).

To exit the terminal interface, press `Q` or `Esc` on the main menu. The application asks **Do you want to exit?**, with **No** selected by default. Use the arrow keys and `Enter` to choose **No** or **Yes**, or press `Y` to exit and `N` or `Esc` to cancel. In the package and restore-point views, `Q` or `Esc` returns to the main menu.

### Terminal controls

| View | Controls |
|---|---|
| Main menu | Up/down arrows or Tab to move; Enter to open; `R` to refresh; `Q` or Esc to request exit |
| Packages and applications | Arrows or Page Up/Down to browse; Space to select; `/` to search; `C` to clear selection; `P` to preview removal |
| Dependency removal | `D` in the package view toggles unused-dependency removal for APT and Pacman |
| Restore points | Arrows to browse; `N` to create; `D` to delete a saved list; `P` to preview cleanup; `C` to toggle APT cache cleanup |
| Preview | Arrows or Page Up/Down to scroll; Enter or Esc to close the preview, followed by a separate apply confirmation; `Y` applies, any other key cancels |
| Language | Arrows and Enter to select; Esc to return; number shortcuts also work |

Protected packages are marked with `!` and cannot be selected. Selected packages remain selected across searches and package views until cleared. On servers without desktop application entries, use **All packages** even if **Applications** is empty.

To add a desktop-menu entry:

```sh
python3 install-menu.py
```

The installed program uses `~/.local/share/linux-tvarka/` for compatibility with earlier versions. An existing `XDG_DATA_HOME` is respected. No personal restore points are included in this repository; create your own on each computer.

## Portable mode

```sh
sh portable.sh
```

Force the terminal interface with `sh portable.sh --tui`. Otherwise, the portable launcher uses the same graphical-session detection as `start`.

Alternatively, create the portable-mode marker and use the executable launcher:

```sh
touch portable.mode
./start
```

Portable settings and restore points are stored in `portable-data/`, separately for each machine. The directory must be writable. This is portable source code, **not a self-contained AppImage**: required host libraries are checked and, when missing, installed through the native package manager.

## Restore points

1. Review your installed software and create a point when the package selection suits your needs.
2. Later, choose that point and preview the proposed cleanup.
3. Review the package list and confirm only the changes you intend.

New dependencies required by retained packages and protected system components may remain. Missing baseline packages are reported rather than reinstalled. Deleting a restore point deletes its saved list, not installed applications.

## Settings

Open **Settings** for language selection and **About**. The About window contains the project goals, current implementation limits, license text and an optional PayPal support link.

English is the default when no valid language preference is saved, regardless of the system language. An explicitly selected language is remembered on the next launch. In the terminal interface, open **Language** from the main menu, select with the arrow keys, and press `Enter`. Portable mode loads preferences from its machine-specific portable data directory. Menu labels and About text use the selected language; some terminal prompts and help text remain in English.

## Development checks

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q .
```

The included tests cover language defaults and persistence, manager detection, dependency checks, headless desktop-entry discovery, terminal navigation and exit confirmation, root startup and privilege-command selection, dependency retention, point deletion and selected command-safety checks. The terminal interface has also been launched against an Ubuntu/WSL package inventory. These checks do not prove that removal works correctly on every supported distribution; no real package-removal transaction was performed as part of these interface checks.

## License and artwork

Application source: **GNU GPL version 3 only** (`GPL-3.0-only`), without warranty. See [LICENSE](LICENSE).

The GNU head links to the GNU Project. Its artwork has a separate CC BY-SA 2.0 license; see [LICENSE-GNU-ICON.md](LICENSE-GNU-ICON.md) and [NOTICE](NOTICE). This application is independent and does not claim GNU endorsement.

## Support

Optional support: [paypal.me/grygaz](https://paypal.me/grygaz).
