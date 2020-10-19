import Fuse from 'fuse.js'
import { ReactElement, useEffect, useState } from 'react'
import Select from 'react-select/async'
import s from 'styled-components'

import {
  BORDER,
  CLUBS_GREY,
  CLUBS_GREY_LIGHT,
  FOCUS_GRAY,
  MEDIUM_GRAY,
  WHITE,
} from '../constants/colors'
import { MD, mediaMaxWidth } from '../constants/measurements'
import { Icon, SelectedTag } from './common'

const SearchWrapper = s.div`
  margin-bottom: 30px;
  overflow: visible;

  ${mediaMaxWidth(MD)} {
    height: auto;
    overflow: visible;
    width: 100%;
    margin: 0;
    padding: 8px 1rem;
    border-bottom: 1px solid ${BORDER};
    position: fixed;
    left: 0;
    z-index: 1000;
    background: ${WHITE};
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.075);
  }
`

const SubLabel = s.div`
  font-size: 0.9em;
  color: ${CLUBS_GREY_LIGHT};

  .tag & {
    display: none;
  }
`

const ColorPreview = s.div<{ color: string }>`
  display: inline-block;
  width: 1em;
  height: 1em;
  background-color: #${({ color }) => color};
  border: 1px solid black;
  border-radius: 3px;
  margin-right: 5px;
  vertical-align: middle;
`

const SearchIcon = s(Icon)`
  cursor: pointer;
  color: ${MEDIUM_GRAY};
  opacity: 0.5;
  margin-right: 6px !important;

  ${mediaMaxWidth(MD)} {
    right: 24px;
  }
`

type SearchOption = { label: string; options: FuseTag[] }

type SearchProps = {
  selected: FuseTag[]
  searchTags: (query: string) => Promise<SearchOption[]>
  recommendedTags: SearchOption[]
  updateTag: (tag: FuseTag, name: string) => void
  clearTags: () => void
  name: string
}

const Search = ({
  name,
  selected = [],
  searchTags,
  recommendedTags,
  updateTag,
  clearTags,
}: SearchProps): ReactElement => {
  // Custom styles for the react-select
  const styles = {
    control: ({ background, ...base }, { isFocused, isSelected }) => {
      const isEmphasized = isFocused || isSelected
      return {
        ...base,
        border: `1px solid ${BORDER}`,
        background: isEmphasized ? FOCUS_GRAY : background,
        boxShadow: 'none',
        '&:hover': {
          background: FOCUS_GRAY,
        },
      }
    },
    option: ({ background, ...base }, { isFocused, isSelected }) => {
      const isEmphasized = isFocused || isSelected
      return {
        ...base,
        background: isEmphasized ? FOCUS_GRAY : background,
        color: CLUBS_GREY,
      }
    },
  }

  // Overriding specific components of the react-select
  const components = {
    IndicatorSeparator: () => null,
    DropdownIndicator: () => <SearchIcon name="tag" />,
    MultiValueContainer: ({ innerProps, children }) => {
      return (
        <SelectedTag {...innerProps} className="tag is-rounded has-text-white">
          {children}
        </SelectedTag>
      )
    },
    MultiValueLabel: ({ data: { label } }) => label,
    MultiValueRemove: ({
      data,
      innerProps: { onClick, onTouchEnd, onMouseDown },
    }) => {
      const removeGenerator = (func) => {
        return (e) => {
          func(e)
          updateTag(data, name)
        }
      }
      return (
        <button
          className="delete is-small"
          onClick={removeGenerator(onClick)}
          onTouchEnd={removeGenerator(onTouchEnd)}
          onMouseDown={removeGenerator(onMouseDown)}
        />
      )
    },
  }
  return (
    <Select
      instanceId={`club-search-${name}`}
      isMulti
      cacheOptions
      styles={styles}
      components={components}
      loadOptions={searchTags}
      defaultOptions={recommendedTags}
      value={selected}
      backspaceRemovesValue
      onChange={(_, selectEvent): void => {
        const { action, option, removedValue } = selectEvent
        if (action === 'select-option') {
          updateTag(option, name)
        } else if (action === 'pop-value') {
          // pop-value events contain removedValue = undefined if no tags are selected
          removedValue && updateTag(removedValue, name)
        } else if (action === 'clear') {
          clearTags()
        }
      }}
      placeholder={`Search for ${name.toLowerCase()}`}
    />
  )
}

const selectInitial = (name: string, tags: FuseTag[] = []) => {
  return [
    {
      label: `All ${name.toLowerCase()}`,
      options: tags,
    },
  ]
}

export type FuseTag = {
  value: number | string
  label: string | ReactElement
  text?: string
  count?: number
  color?: string
  name?: string
  description?: string
}

type FilterProps = {
  name: string
  tags: FuseTag[]
  updateTag: (tag: FuseTag, name: string) => void
  selected: FuseTag[]
  clearTags: () => void
}

const Filter = ({
  name,
  tags,
  updateTag,
  clearTags,
  selected,
}: FilterProps): ReactElement => {
  const filter = new Set()
  selected.forEach(({ value }) => filter.add(value))

  // add count annotation to label
  tags = tags
    .filter(({ value }) => !filter.has(value))
    .map(({ label, count, color, description, ...tag }) => ({
      ...tag,
      text: label as string,
      label: (
        <>
          {color != null && <ColorPreview color={color}> </ColorPreview>}
          {`${label}${count != null ? ` (${count})` : ''}`}
          {!!description && <SubLabel>{description}</SubLabel>}
        </>
      ),
    }))

  const fuseOptions = {
    keys: ['text'],
    tokenize: true,
    findAllMatches: true,
    shouldSort: true,
    minMatchCharLength: 2,
    threshold: 0.2,
  }
  const fuse = new Fuse<FuseTag>(tags, fuseOptions)

  const [recommendedTags, setRecommendedTags] = useState(
    selectInitial(name, tags),
  )
  const searchTags = async (query: string) => [
    {
      label:
        query.length > 0
          ? `Matched ${name.toLowerCase()}`
          : `All ${name.toLowerCase()}`,
      options: fuse.search(query).map((result) => result.item),
    },
  ]

  useEffect(() => {
    setRecommendedTags(selectInitial(name, tags))
  }, [selected])

  return (
    <>
      <SearchWrapper>
        <Search
          name={name}
          selected={selected}
          searchTags={searchTags}
          recommendedTags={recommendedTags}
          updateTag={updateTag}
          clearTags={clearTags}
        />
      </SearchWrapper>
    </>
  )
}

export default Filter
