# Linux Fresh Install recovery application

The application aims to **restore a Linux distribution as closely as possible to a fresh installation**, without reinstalling the entire operating system.

Its main goal is to remove user-installed applications, additional packages and their configuration, returning the system to its initial state while retaining the standard distribution installation and official system updates.

## How it works

The application analyses the current system to identify packages and applications belonging to:

- the original distribution installation;
- official system updates;
- applications installed later by the user;
- additional dependencies and unnecessary packages.

During restoration, user-added applications are removed, leaving **the distribution’s default applications and their official updates**.

## Intended outcome

After restoration, the system should resemble a clean Linux installation with all official system updates released up to the time of restoration.

The application should not downgrade packages. Its goal is to restore **a clean selection of system software**, rather than necessarily restoring old package versions.

## Main features

- Automatic inventory of installed packages.
- Distinguishing system packages from user-installed packages.
- Removing applications added by the user.
- Cleaning unnecessary dependencies and leftover packages.
- Repairing the package manager’s state.
- Retaining official distribution updates.
- An option to preserve system configuration and user data.
- A dry-run mode showing what will be removed before restoration.
- A restoration log recording all actions performed.

## Safety

Because the application changes the system’s package state, backing up important data before restoration is recommended.

The application should not automatically remove packages essential for booting or basic system operation. Before applying changes, the user must receive a clear summary of the packages and applications to be removed.

## Final result

**Fresh Install Restore** aims to return Linux to a clean, standard software state:

> **Default distribution applications + official system updates − applications added by the user.**

This makes it possible to clean the system and return to a fresh software environment without reinstalling the entire operating system.
