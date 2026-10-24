# Atelier typography

Hanken Grotesk 400 is self-hosted here, unmodified, under the supplied SIL OFL.
Sources: the Hanken Grotesk family in [Google Fonts](https://github.com/google/fonts/tree/main/ofl/hankengrotesk)
and its official Google Fonts CSS/WOFF2 delivery. Latin and Latin Extended are
separate official subsets. `Hanken-OFL.txt` retains the copyright/license notice.

Sentient 300/400 is loaded through [Fontshare's official stylesheet API](https://api.fontshare.com/v2/css?f[]=sentient@300,400&display=swap).
It is **not bundled in this public repository**: the supplied ITF FFL permits
web use/self-hosting but restricts redistribution through repositories. Users
who want to self-host should obtain their own unmodified copy directly from
[Fontshare](https://www.fontshare.com/fonts/sentient) and review the
[ITF Free Font License](https://www.fontshare.com/licenses/itf-ffl).

Builds do not fetch fonts. Browser rendering uses the Fontshare service for
Sentient, with Georgia as the available fallback; Hanken Grotesk falls back to
Arial. No font files were converted, edited or subsetted by this project.
