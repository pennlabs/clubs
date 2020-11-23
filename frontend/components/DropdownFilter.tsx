import { ReactElement } from 'react'
import styled from 'styled-components'

import { BORDER, CLUBS_GREY, LIGHT_GRAY } from '../constants/colors'
import {
  ANIMATION_DURATION,
  MD,
  mediaMaxWidth,
} from '../constants/measurements'
import { logEvent } from '../utils/analytics'
import { Icon } from './common'

const Line = styled.hr`
  background-color: ${BORDER};
  height: 2px;
  margin: 0;
  margin-top: 30px;
  padding: 0;

  ${mediaMaxWidth(MD)} {
    display: none !important;
  }
`

const DropdownHeader = styled.div`
  display: flex;
  justify-content: space-between;
  padding: 7px 3px;
  cursor: pointer;

  ${mediaMaxWidth(MD)} {
    display: inline-flex;
    padding: 4px 8px;
    margin-right: 6px;
    border-radius: 16px;
    font-size: 80%;
    color: ${LIGHT_GRAY};
  }
`

const CheckboxRow = styled.div<{ color?: string }>`
  padding-top: 3px;

  & label {
    cursor: pointer;
  }

  & span {
    color: ${({ color }) => color ?? CLUBS_GREY};
  }

  & span[role='checkbox'] {
    float: left;
  }
`

const TableWrapper = styled.div`
  overflow: hidden;

  max-height: 150vh;
  opacity: 1;

  ${mediaMaxWidth(MD)} {
    width: 100%;
  }
`

const TableContainer = styled.div`
  ${mediaMaxWidth(MD)} {
    padding: 1rem;
  }
`

const Chevron = styled(Icon)<{ open?: boolean }>`
  cursor: pointer;
  color: ${CLUBS_GREY};
  transform: rotate(0deg) translateY(0);
  transition: transform ${ANIMATION_DURATION}ms ease;
  ${({ open }) => open && 'transform: rotate(180deg) translateY(-4px);'}

  ${mediaMaxWidth(MD)} {
    margin-top: 0.1em !important;
    margin-left: 0.1em !important;
    color: ${LIGHT_GRAY};
    ${({ open }) => open && 'transform: rotate(180deg)'}
  }
`

const DropdownHeaderText = styled.p`
  opacity: 0.8;
  font-weight: 600;
  margin-bottom: 0;
`

type FilterHeaderProps = {
  active: boolean
  name: string
  id?: string
  toggleActive: () => void
}

// TODO: export out into separate component?
export const FilterHeader = ({
  active,
  name,
  id,
  toggleActive,
}: FilterHeaderProps): ReactElement => (
  <>
    <Line />
    <DropdownHeader onClick={() => toggleActive()}>
      <DropdownHeaderText id={id}>{name}</DropdownHeaderText>
      <Chevron
        name="chevron-down"
        alt="toggle dropdown"
        open={active}
        size="1rem"
      />
    </DropdownHeader>
  </>
)

export type SelectableTag = {
  value: number | string
  label: string
  name: string
  count?: number
}

type DropdownFilterProps = {
  name: string
  color?: string
  selected: SelectableTag[]
  options: SelectableTag[]
  updateTag: (tag: SelectableTag, name: string) => void
}

const DropdownFilter = ({
  selected,
  name,
  color,
  options,
  updateTag,
}: DropdownFilterProps): ReactElement => {
  /**
   * Returns if the supplied tag is in the list of selected tags
   *
   * @param {{value: string}} tag
   */
  const isSelected = (tag: SelectableTag): boolean => {
    const { value } = tag
    return Boolean(selected.find((tag) => tag.value === value))
  }

  return (
    <TableWrapper>
      <TableContainer>
        {options.map((tag: SelectableTag) => (
          <CheckboxRow
            key={tag.label}
            color={color}
            onClick={() => {
              logEvent('filter', name)
              updateTag(tag, name)
            }}
          >
            <label>
              <span
                role="checkbox"
                tabIndex={0}
                aria-checked={isSelected(tag) ? 'true' : 'false'}
              >
                <Icon
                  style={{ fill: color }}
                  name={isSelected(tag) ? 'check-box' : 'box'}
                  alt={isSelected(tag) ? 'selected' : 'not selected'}
                />
                &nbsp;
              </span>
              <span>
                <p>
                  {tag.label}
                  {typeof tag.count !== 'undefined' && (
                    <span className="has-text-grey"> ({tag.count})</span>
                  )}
                </p>
              </span>
            </label>
          </CheckboxRow>
        ))}
      </TableContainer>
    </TableWrapper>
  )
}

export default DropdownFilter
