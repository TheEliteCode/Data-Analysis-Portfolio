# Publish this portfolio on GitHub Pages

This portfolio replaces the current default Jekyll landing page in your `TheEliteCode/Data-Analysis-Portfolio` repository. The files in this package are a static website and work with GitHub Pages on GitHub Free when the repository is public.

## Upload using GitHub in your browser

1. Download `david-alexander-portfolio.zip` and choose **Extract All** on your computer.
2. Open [your Data-Analysis-Portfolio repository](https://github.com/TheEliteCode/Data-Analysis-Portfolio) and make sure you are signed in.
3. Choose **Add file** → **Upload files**. Upload these files to the repository root: `index.html`, `projects.js`, `render-projects.js`, `EDITING-GUIDE.md`, and `PUBLISHING-GUIDE.md`. Also upload `files/README.md` keeping the `files` folder path.
4. Review the change summary. Choose **Commit directly to the main branch** (or make a branch and pull request if you prefer), then commit.
5. In the repository, open **Settings** → **Pages**. Under **Build and deployment**, choose **Deploy from a branch**, then select `main` and `/(root)`, and save. If it is already set to `main` and `/(root)`, leave it as is.
6. Open [the portfolio website](https://theelitecode.github.io/Data-Analysis-Portfolio/) after the Pages deployment finishes. GitHub notes that a first publish or an update can take several minutes.

The site is public, so only upload files you are comfortable sharing. Do not upload client data or confidential research data. The project cards currently point to public GitHub projects; the other work has no public file links yet.

## Add or edit a project later

Edit `projects.js` in the repository. Copy a project object in `EDITING-GUIDE.md`, edit its fields and links, then commit the change. To host an attachment with the site, upload it under `files/<project-folder>/` and add a relative link such as `files/cyclistic/chart.png` to that project's `links` list.
