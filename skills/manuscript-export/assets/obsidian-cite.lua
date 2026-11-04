-- MIT, BC (Brain Trinity). Handles pre-3.8 title and current wikilink class.
function Link(el)
  if not (el.title == 'wikilink' or el.classes:includes('wikilink')) then return nil end
  local target = el.target:gsub('%%(%x%x)', function(hex) return string.char(tonumber(hex, 16)) end)
  local key = target:match('^@([^/#|]+)$') or target:match('/@([^/#|]+)$')
  if key then
    return pandoc.Cite({pandoc.Str('@' .. key)}, {pandoc.Citation(key, 'NormalCitation')})
  end
  return el.content
end

function BlockQuote(el)
  local first = el.content[1]
  if first and (first.t == 'Para' or first.t == 'Plain') and first.content[1]
     and first.content[1].t == 'Str' then
    local text = first.content[1].text
    if text:match('^%[![%w_-]+%][+-]?$') then
      table.remove(first.content, 1)
      while first.content[1] and first.content[1].t == 'Space' do table.remove(first.content, 1) end
      -- Obsidian callout titles remain as text, content is never discarded.
    end
  end
  return el
end
