# Editing your portfolio

The page design is in `index.html`. Your project cards are kept separately in `projects.js`, so you can add or edit projects without changing the design. `render-projects.js` displays the cards; you normally do not need to edit it.

## Add a project

1. Open `projects.js` and add a new object inside the `window.portfolioProjects` list. Put a comma after the previous object.
2. Fill in `title`, `type`, `summary`, `finding`, `tools`, and `links`.
3. Each link is a pair of `label` and `url`. Use a full GitHub URL for a file already in a repository, or a relative path for a file uploaded into this portfolio, such as `files/cyclistic/chart.png`.
4. Save/commit `projects.js`. The site updates after GitHub Pages deploys.

Example (copy the object and replace its details):

```js
{
  "title": "Project name",
  "type": "Personal project",
  "summary": "What question the project addressed and what you did.",
  "finding": "A result you can support with your analysis.",
  "tools": ["SQL", "Python", "Power BI"],
  "links": [
    { "label": "Notebook", "url": "files/project-name/analysis.ipynb" },
    { "label": "Dashboard", "url": "https://github.com/your-name/repository/blob/main/dashboard.png" }
  ]
}
```

## Add files

Create a folder under `files/` for the project (for example, `files/cyclistic/`), upload the file there, then add a link to its relative path in that project's `links` list. Use simple filenames without spaces where possible. For large files, use a GitHub repository link instead of uploading them here.

## Edit your details or page design

Edit the text in `index.html` for your introduction, experience, education, skills or contact details. Edit its `<style>` section only if you want to change the colors, spacing or layout. Keep `index.html`, `projects.js`, and `render-projects.js` together in the publishing folder.

## Keep project claims accurate

Use only findings you can explain and support. For collaboration work, describe your own contribution clearly. For the health-data research work listed here, the entry is limited to data cleaning and transformation because the final report was not available to you.
