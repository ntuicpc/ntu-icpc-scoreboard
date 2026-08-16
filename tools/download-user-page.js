const pathParts = window.location.pathname
    .split("/")
    .filter(Boolean);

const teamname = decodeURIComponent(pathParts.at(-1))
    .replace(/[<>:"/\\|?*\x00-\x1F]/g, "_");

const blob = new Blob(
    [document.documentElement.outerHTML],
    { type: "text/html;charset=utf-8" }
);

const link = document.createElement("a");
link.href = URL.createObjectURL(blob);
link.download = `${teamname}.html`;

document.body.appendChild(link);
link.click();
link.remove();

setTimeout(() => {
    URL.revokeObjectURL(link.href);
}, 1000);