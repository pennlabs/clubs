import React, {
  ReactElement,
  SetStateAction,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react'
import styled from 'styled-components'

import {
  ALLBIRDS_GRAY,
  BLACK_ALPHA,
  CLUBS_GREY,
  FOCUS_GRAY,
  H1_TEXT,
  MEDIUM_GRAY,
  WHITE,
} from '../constants/colors'
import {
  BORDER_RADIUS,
  FULL_NAV_HEIGHT,
  MD,
  mediaMaxWidth,
  NAV_HEIGHT,
} from '../constants/measurements'
import { BODY_FONT } from '../constants/styles'
import { Icon } from './common'
import DropdownFilter, { FilterHeader, SelectableTag } from './DropdownFilter'
import FilterSearch, { FuseTag } from './FilterSearch'
import OrderInput from './OrderInput'

export const SearchbarRightContainer = styled.div`
  width: 80vw;
  margin-left: 20vw;
  padding: 0;

  ${mediaMaxWidth(MD)} {
    width: 100%;
    margin-left: 0;
  }
`

const Wrapper = styled.div`
  height: 100vh;
  width: 20vw;
  overflow-x: hidden;
  overflow-y: auto;
  position: fixed;
  top: 0;
  padding-top: ${NAV_HEIGHT};
  color: ${H1_TEXT};

  ${mediaMaxWidth(MD)} {
    padding-top: 0px !important;
    position: relative;
    height: auto;
    overflow: visible;
    padding-top: 0;
    width: 100%;
  }
`

const SearchWrapper = styled.div`
  margin-bottom: 30px;

  ${mediaMaxWidth(MD)} {
    margin-bottom: 8px;
  }
`

const Content = styled.div<{ show?: boolean }>`
  padding: 12px 17px 12px 17px;
  width: 100%;

  &::-webkit-scrollbar {
    display: none;
  }

  .mobile-only {
    display: none;
  }

  ${mediaMaxWidth(MD)} {
    display: ${({ show }) => (show ? 'block' : 'none')};
    overflow-x: hidden;
    width: 100%;
    margin: 0;
    padding: 16px 1rem;
    position: fixed;
    z-index: 1000;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.075);
    background: ${WHITE};
    top: ${NAV_HEIGHT};

    .mobile-only {
      display: block;
    }
  }
`

const MobileToggle = styled.button`
  display: none;
  ${mediaMaxWidth(MD)} {
    z-index: 999;
    display: block;
    position: fixed;
    top: ${NAV_HEIGHT};
    right: 16px;
    background-color: ${WHITE};
    padding: 5px 8px;
    border-radius: 0 0 5px 5px;
    border: 1px solid ${BLACK_ALPHA(0.1)};
    border-top: 0;
    cursor: pointer;
  }
`

const Input = styled.input`
  border: 1px solid ${ALLBIRDS_GRAY};
  outline: none;
  color: ${CLUBS_GREY};
  width: 100%;
  font-size: 1em;
  padding: 8px 10px;
  background: ${WHITE};
  border-radius: ${BORDER_RADIUS};
  font-family: ${BODY_FONT};

  &:hover,
  &:active,
  &:focus {
    background: ${FOCUS_GRAY};
  }
`

const SearchIcon = styled.span`
  cursor: pointer;
  color: ${MEDIUM_GRAY};
  opacity: 0.5;
  padding-top: 4px;
  position: absolute;
  right: 24px;

  ${mediaMaxWidth(MD)} {
    right: 24px;
  }
`

const MobileLine = styled.hr`
  display: none;
  ${mediaMaxWidth(MD)} {
    display: block;
    margin: 1em 0 0 0;
    border-color: ${CLUBS_GREY};
  }
`

type SearchBarProps = React.PropsWithChildren<{
  updateSearch: (modifier: SetStateAction<SearchInput>) => void
  searchInput: SearchInput
}>

type CollapsibleProps = React.PropsWithChildren<{
  active?: boolean
  name: string
}>

const Collapsible = ({
  children,
  active,
  name,
}: CollapsibleProps): ReactElement => {
  const [isActive, setActive] = useState<boolean | null>(active ?? null)
  const [defaultActive, setDefaultActive] = useState<boolean>(true)

  useEffect(() => {
    const onResize = () => {
      setDefaultActive(window.innerWidth >= parseInt(MD))
    }
    onResize()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  const groupLabelId = `collapsible-group-${name
    .replace(/\s/g, '-')
    .toLowerCase()}`

  return (
    <div role="group" aria-labelledby={groupLabelId}>
      <FilterHeader
        active={isActive ?? defaultActive}
        name={name}
        id={groupLabelId}
        toggleActive={() => setActive((active) => !(active ?? defaultActive))}
      />
      {(isActive ?? defaultActive) && children}
    </div>
  )
}

export type SearchInput = {
  [key: string]: string
}

export type SearchTag = {
  name: string
  label: string
  value: string | number
}

const SearchBarContext = React.createContext<
  null | ((modifier: SetStateAction<SearchInput>) => void)
>(null)

const SearchBarValueContext = React.createContext<SearchInput>({})

type SearchBarTagItemProps = {
  param: string
  label: string
  options: FuseTag[]
}

type SearchBarTextItemProps = {
  param: string
}

type SearchBarOptionItemProps = {
  param: string
  label: string
}

type SearchBarCheckboxItemProps = {
  param: string
  label: string
  options: (SearchTag & { color?: string })[]
}

/**
 * Convert the comma separated string of tag values into a list of tag objects.
 */
function paramsToTags<T extends { value: string | number }>(
  params: string | null | undefined,
  tags: T[],
): T[] {
  const tagValues = (params ?? '')
    .trim()
    .split(',')
    .filter((val) => val.length > 0)

  return tagValues
    .map((val) => tags.find((tag) => tag.value.toString() === val))
    .filter((tag) => tag !== undefined) as T[]
}

/**
 * A item in the search bar that renders as a group of checkboxes.
 */
export const SearchBarCheckboxItem = ({
  param,
  label,
  options,
}: SearchBarCheckboxItemProps): ReactElement => {
  const searchCallback = useContext(SearchBarContext)
  if (searchCallback == null) {
    throw new Error('This component must be used inside a search bar!')
  }

  const searchValue = useContext(SearchBarValueContext)

  const [tags, setTags] = useState<SelectableTag[]>([])

  useEffect(() => {
    setTags(paramsToTags(searchValue[param], options))
  }, [searchValue])

  return (
    <Collapsible name={label}>
      <DropdownFilter
        name={param}
        options={options}
        selected={tags}
        updateTag={(tag) => {
          setTags((prev) => {
            const newArr = toggleItemInArray(
              tag,
              prev,
              (a, b) => a.value === b.value,
            )
            searchCallback(getCallback(param, newArr))
            return newArr
          })
        }}
      />
    </Collapsible>
  )
}

/**
 * A item in the search bar that renders as a single select dropdown menu.
 */
export const SearchBarOptionItem = ({
  param,
  label,
}: SearchBarOptionItemProps): ReactElement => {
  const searchCallback = useContext(SearchBarContext)
  if (searchCallback == null) {
    throw new Error('This component must be used inside a search bar!')
  }

  return (
    <Collapsible name={label}>
      <OrderInput
        onChange={(order: string) =>
          searchCallback((inpt) => ({
            ...inpt,
            [param]: order,
            seed: new Date().getTime().toString(),
          }))
        }
      />
    </Collapsible>
  )
}

/**
 * A item in the search bar that renders as a text input.
 */
export const SearchBarTextItem = ({
  param,
}: SearchBarTextItemProps): ReactElement => {
  const searchCallback = useContext(SearchBarContext)
  if (searchCallback == null) {
    throw new Error('This component must be used inside a search bar!')
  }

  const [nameInput, setNameInput] = useState<string>('')
  const [timeout, storeTimeout] = useState<number | null>(null)
  const inputRef = useRef() as React.MutableRefObject<HTMLInputElement>

  useEffect(() => {
    timeout !== null && clearTimeout(timeout)
    const timeoutId: number = window.setTimeout(
      () =>
        searchCallback((inpt) => {
          if (nameInput.length <= 0) {
            const newInpt = { ...inpt }
            if (param in newInpt) {
              delete newInpt[param]
            }
            return newInpt
          }
          return { ...inpt, [param]: nameInput }
        }),
      200,
    )
    storeTimeout(timeoutId)
  }, [nameInput])

  const focus = () => inputRef.current && inputRef.current.focus()

  const isTextInSearchBar = Boolean(nameInput)
  return (
    <>
      <SearchWrapper>
        <SearchIcon>
          {isTextInSearchBar ? (
            <Icon
              name="x"
              alt="cancel search"
              onClick={() => {
                setNameInput('')
                focus()
              }}
            />
          ) : (
            <Icon name="search" alt="search" onClick={focus} />
          )}
        </SearchIcon>
        <Input
          type="text"
          name="search"
          placeholder="Search"
          aria-label="Search"
          ref={inputRef}
          value={nameInput}
          onChange={(e) => setNameInput(e.target.value)}
        />
      </SearchWrapper>
      <MobileLine />
    </>
  )
}

function toggleItemInArray<T>(
  item: T,
  arr: T[],
  comparator: (a: T, b: T) => boolean,
): T[] {
  const newState = [...arr]
  const itemIndex = newState.findIndex((otherItem) =>
    comparator(item, otherItem),
  )
  if (itemIndex === -1) {
    newState.push(item)
  } else {
    newState.splice(itemIndex, 1)
  }
  return newState
}

const getCallback = (key: string, tags: SearchTag[]) => {
  const updateSearchState = (state) => {
    if (tags.length <= 0) {
      const newState = { ...state }
      if (key in newState) {
        delete newState[key]
      }
      return newState
    }
    return { ...state, [key]: tags.map((tag) => tag.value).join(',') }
  }

  return updateSearchState
}

/**
 * An item in the search bar that renders a multiselect of selectable tags.
 */
export const SearchBarTagItem = ({
  param,
  options,
  label,
}: SearchBarTagItemProps): ReactElement => {
  const searchCallback = useContext(SearchBarContext)
  if (searchCallback == null) {
    throw new Error('This component must be used inside a search bar!')
  }

  const searchValue = useContext(SearchBarValueContext)

  const [tags, setTags] = useState<FuseTag[]>([])

  useEffect(() => {
    setTags(paramsToTags(searchValue[param], options))
  }, [searchValue])

  const updateTag = (tag: FuseTag) => {
    const selectedTags = toggleItemInArray(
      tag,
      tags,
      (a, b) => a.value === b.value,
    )
    searchCallback(
      getCallback(
        param,
        selectedTags.map((tag) => {
          tag.name = label
          return tag
        }) as SearchTag[],
      ),
    )
  }

  return (
    <Collapsible name={label}>
      <FilterSearch
        param={param}
        name={label}
        tags={options}
        updateTag={updateTag}
        selected={tags}
        clearTags={() => {
          searchCallback(getCallback(param, []))
        }}
      />
    </Collapsible>
  )
}

/**
 * A search bar that returns a search query based on filtering on multiple attributes.
 */
const SearchBar = ({
  updateSearch,
  searchInput,
  children,
}: SearchBarProps): ReactElement => {
  const [scrollAmount, setScrollAmount] = useState<number>(
    parseFloat(FULL_NAV_HEIGHT),
  )
  const [mobileShow, setMobileShow] = useState<boolean>(false)

  useEffect(() => {
    const onScroll = () => {
      const scrollPercent = 1 - Math.max(0, Math.min(window.scrollY / 150, 1))
      const topDistance =
        scrollPercent * (parseFloat(FULL_NAV_HEIGHT) - parseFloat(NAV_HEIGHT)) +
        parseFloat(NAV_HEIGHT)
      setScrollAmount(topDistance)
    }
    onScroll()
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <>
      <Wrapper style={{ paddingTop: `${scrollAmount}rem` }}>
        <Content show={mobileShow}>
          <SearchBarValueContext.Provider value={searchInput}>
            <SearchBarContext.Provider value={updateSearch}>
              {children}
            </SearchBarContext.Provider>
          </SearchBarValueContext.Provider>
          <div className="has-text-centered mobile-only">
            <button
              type="button"
              className="button is-light is-small"
              onClick={(e) => {
                e.preventDefault()
                setMobileShow(false)
              }}
              onKeyPress={(e) => {
                if (e.code === 'Space' || e.code === 'Enter') {
                  e.preventDefault()
                  setMobileShow(false)
                }
              }}
            >
              Hide Menu
            </button>
          </div>
        </Content>
        <MobileToggle
          onClick={(e) => {
            e.preventDefault()
            setMobileShow(true)
          }}
          onKeyPress={(e) => {
            if (e.code === 'Space' || e.code === 'Enter') {
              e.preventDefault()
              setMobileShow(true)
            }
          }}
        >
          <Icon name="search" />
        </MobileToggle>
      </Wrapper>
    </>
  )
}

export default SearchBar
