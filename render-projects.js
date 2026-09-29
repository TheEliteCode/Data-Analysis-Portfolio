/* Renders project cards from projects.js. */
(() => {
  const grid = document.getElementById('project-grid');
  const items = Array.isArray(window.portfolioProjects) ? window.portfolioProjects : [];
  const make = (tag, cls, text) => {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text !== undefined) el.textContent = text;
    return el;
  };
  items.forEach((project, index) => {
    const card = make('article', 'card');
    const top = make('div', 'card-top');
    top.append(make('span', 'number', String(index + 1).padStart(2, '0')));
    top.append(make('span', 'kind', project.type || 'Project'));
    card.append(top, make('h3', '', project.title || 'Untitled project'));
    if (project.summary) card.append(make('p', '', project.summary));
    if (project.finding) {
      const finding = make('p', 'result');
      finding.append(make('strong', '', 'Finding: '), document.createTextNode(project.finding));
      card.append(finding);
    }
    if (Array.isArray(project.tools) && project.tools.length) {
      const tags = make('div', 'tags');
      tags.setAttribute('aria-label', 'Tools used');
      project.tools.forEach(tool => tags.append(make('span', 'tag', tool)));
      card.append(tags);
    }
    if (Array.isArray(project.links) && project.links.length) {
      const links = make('div', 'project-links');
      links.setAttribute('aria-label', 'Project files and links');
      project.links.forEach(item => {
        if (!item || !item.label || !item.url) return;
        const link = make('a', 'project-link', item.label);
        link.href = item.url;
        if (/^https?:\/\//i.test(item.url)) {
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
        }
        links.append(link);
      });
      if (links.childElementCount) card.append(links);
    }
    grid.append(card);
  });
})();
