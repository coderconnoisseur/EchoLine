.pragma library

function escape(text) {
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
}

// What a caption line shows: settled words only ("hide"), or settled words plus
// the words that may still change, dimmed ("dim"). Finished lines are all settled.
function markup(text, settled, mode, color) {
    if (mode === "hide")
        return escape(settled)
    if (!text.startsWith(settled) || text.length === settled.length)
        return escape(text)
    return escape(settled) + '<font color="#8c' + color.slice(1) + '">' + escape(text.slice(settled.length)) + "</font>"
}
