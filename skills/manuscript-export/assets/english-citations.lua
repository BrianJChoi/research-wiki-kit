-- MIT, BC (Brain Trinity). Render citations in English, preserve manuscript language.
function Pandoc(doc)
  local language = doc.meta.lang
  doc.meta.lang = pandoc.MetaString('en-US')
  doc = pandoc.utils.citeproc(doc)
  doc.meta.lang = language
  return doc
end
