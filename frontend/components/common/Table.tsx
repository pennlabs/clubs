import { ReactElement, useEffect, useMemo, useState } from 'react'
import Select from 'react-select'
import {
  useFilters,
  useGlobalFilter,
  usePagination,
  useSortBy,
  useTable,
} from 'react-table'
import styled from 'styled-components'

import {
  ALLBIRDS_GRAY,
  BORDER,
  CLUBS_GREY,
  FOCUS_GRAY,
  LIGHT_GRAY,
  WHITE,
} from '../../constants/colors'
import { BORDER_RADIUS, MD, mediaMaxWidth } from '../../constants/measurements'
import { BODY_FONT } from '../../constants/styles'
import { titleize } from '../../utils'
import { Icon } from '.'

const styles = {
  control: ({ background, ...base }) => {
    return {
      ...base,
      border: `1px solid ${BORDER}`,
      boxShadow: 'none',
      width: '100%',
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

type Option = {
  label: string
  key: any
}

type FilterOption = {
  options: Option[]
  label: string
  filterFunction: (a, b) => boolean
}

type Row = { [key: string]: any }

type tableProps = {
  columns: Row[]
  data: Row[]
  searchableColumns: string[]
  filterOptions?: FilterOption[]
}

const Styles = styled.div`
  padding: 1rem;
  width: 100%;
`

const SearchWrapper = styled.div`
  overflow: visible;
  margin: 0px;
  ${mediaMaxWidth(MD)} {
    width: 100%;
    margin: 0;
    border-bottom: 1px solid ${BORDER};
    background: ${WHITE};
  }
`
const Toolbar = styled.div`
  margin-bottom: 50px;
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

const GreyText = styled.span`
  color: ${LIGHT_GRAY};
`

const Table = ({
  columns,
  data,
  searchableColumns,
  filterOptions,
}: tableProps): ReactElement => {
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [tableData, setTableData] = useState<Row[]>([])
  const [selectedFilter, setSelectedFilter] = useState<any>({})
  const [sortedColumn, setSortedColumn] = useState<any>(null)
  useEffect(() => {
    const searchedData = data.filter((item) => {
      if (!searchQuery || searchQuery.length < 3) {
        return true
      }
      return searchableColumns.some((searchId) => {
        const strings = item[searchId].split(' ')
        return strings.some((string) =>
          string.toLowerCase().startsWith(searchQuery.toLowerCase()),
        )
      })
    })
    const filteredData = searchedData.filter((item) => {
      let valid = true
      if (filterOptions) {
        for (const filter in selectedFilter) {
          const original = filterOptions.filter((i) => i.label === filter)[0]
          if (
            selectedFilter[filter] != null &&
            !original.filterFunction(selectedFilter[filter].value, item)
          )
            valid = false
        }
      }
      return valid
    })
    setTableData(filteredData)
  }, [searchQuery, selectedFilter, data])

  const memoColumns = useMemo(
    () =>
      columns.map(({ label, name }) => ({
        Header: label ?? name,
        accessor: name,
      })),
    [data],
  )

  const filterTypes = useMemo(
    () => ({
      text: (rows, id, filterValue) => {
        return rows.filter((row) => {
          const rowValue = row.values[id]
          return rowValue !== undefined
            ? String(rowValue)
                .toLowerCase()
                .startsWith(String(filterValue).toLowerCase())
            : true
        })
      },
    }),
    [],
  )

  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    prepareRow,
    page,
    canPreviousPage,
    canNextPage,
    nextPage,
    pageCount,
    previousPage,
    gotoPage,
    pageOptions,
    state: { pageIndex, pageSize },
  } = useTable(
    {
      columns: memoColumns,
      data: tableData,
      filterTypes,
    },
    useFilters,
    useGlobalFilter,
    useSortBy,
    usePagination,
  )

  const handleSearchChange = (e) => {
    setSearchQuery(e.target.value)
  }

  const handleColumnsSort = (target) => {
    if (sortedColumn && sortedColumn.name === target) {
      if (sortedColumn.status === 'asc') {
        setSortedColumn({ name: sortedColumn.name, status: 'desc' })
      } else {
        setSortedColumn(null)
      }
    } else {
      setSortedColumn({ name: target, status: 'asc' })
    }
  }

  const components = {
    IndicatorSeparator: () => null,
  }

  const handleFilterChange = (newFilter) => {
    const newFilters = { ...selectedFilter }
    newFilters[newFilter.label] = newFilter.value
    setSelectedFilter(newFilters)
  }

  return (
    <Styles>
      <Toolbar>
        <div className="is-pulled-right">
          <SearchWrapper>
            <Input
              className="input"
              value={searchQuery}
              placeholder={`Search ${
                tableData.length < 1 ? data.length : tableData.length
              } entries`}
              onChange={handleSearchChange}
            />
          </SearchWrapper>
        </div>
        <div className="is-pulled-left" style={{ width: '70%' }}>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr 1fr',
            }}
          >
            {filterOptions &&
              filterOptions.map((filterOption) => (
                <div style={{ marginRight: '10px' }}>
                  <Select
                    value={
                      selectedFilter[filterOption.label]
                        ? {
                            label: selectedFilter[filterOption.label].label,
                            value: selectedFilter[filterOption.label].key,
                          }
                        : null
                    }
                    styles={styles}
                    components={components}
                    onChange={(value) =>
                      handleFilterChange({
                        value: value || null,
                        label: filterOption.label ? filterOption.label : null,
                      })
                    }
                    isClearable={true}
                    placeholder={`Filter by ${titleize(filterOption.label)}`}
                    options={filterOption.options.map((option) => {
                      return { value: option.key, label: option.label }
                    })}
                  />
                </div>
              ))}
          </div>
        </div>
      </Toolbar>

      {tableData.length > 0 ? (
        <table className="table is-fullwidth" {...getTableProps()}>
          <thead>
            {headerGroups.map((headerGroup) => (
              <tr {...headerGroup.getHeaderGroupProps()}>
                {headerGroup.headers.map((column) => (
                  <th {...column.getHeaderProps(column.getSortByToggleProps())}>
                    <div onClick={() => handleColumnsSort(column.header)}>
                      {titleize(column.render('Header'))}
                      <span style={{ marginLeft: '1rem' }}>
                        {column.isSorted ? (
                          column.isSortedDesc ? (
                            <Icon name="chevron-down" />
                          ) : (
                            <Icon name="chevron-up" />
                          )
                        ) : sortedColumn === null ? (
                          <Icon name="arrow-vertical" />
                        ) : (
                          ''
                        )}
                      </span>
                    </div>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody {...getTableBodyProps()}>
            {page.map((row) => {
              prepareRow(row)
              return (
                <tr key={row.id} {...row.getRowProps()}>
                  {columns.map((column, i) => {
                    return (
                      <td key={i}>
                        {column.render ? (
                          column.render(row.original.id) ? (
                            column.render(row.original.id)
                          ) : (
                            <GreyText>None</GreyText>
                          )
                        ) : row.original[column.name] ? (
                          row.original[column.name]
                        ) : (
                          <GreyText>None</GreyText>
                        )}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      ) : (
        <h1>No matches were found. Please change your filters.</h1>
      )}
      {pageOptions.length > 1 && (
        <div className="is-clearfix">
          <button
            style={{ marginRight: '0.5rem' }}
            onClick={() => gotoPage(0)}
            disabled={!canPreviousPage}
          >
            <Icon name="chevrons-left" />
          </button>
          <button
            style={{ marginRight: '0.5rem' }}
            onClick={() => previousPage()}            
            disabled={!canPreviousPage}
          >
            <Icon name="chevron-left" />
          </button>
          <select
            value={pageIndex}
            onChange={(e) => gotoPage(Number(e.target.value))}
            className="input is-small"
            style={{ maxWidth: 150, marginRight: '0.5rem' }}
          >
            {pageOptions.map(
              (idx: number): ReactElement => (
                <option value={idx}>Page {idx + 1}</option>
              ),
            )}
          </select>
          <button
            style={{ marginRight: '0.5rem' }}
            onClick={() => nextPage()}
            disabled={!canNextPage}
          >
            <Icon name="chevron-right" />
          </button>
          <button
            style={{ marginRight: '0.5rem' }}
            onClick={() => gotoPage(pageCount - 1)}
            disabled={!canNextPage}
          >
            <Icon name="chevrons-right" />
          </button>
          <div className="is-pulled-right">
            <span>
              {data.length} total entries, {pageSize} entries per page
            </span>
          </div>
        </div>
      )}
    </Styles>
  )
}

export default Table
