import React from 'react'
import s from 'styled-components'
import DropdownFilter from './DropdownFilter'
import { BORDER_RADIUS, mediaMaxWidth, MD, NAV_HEIGHT } from '../constants/measurements'
import {
  MEDIUM_GRAY, HOVER_GRAY, FOCUS_GRAY, CLUBS_GREY
} from '../constants/colors'

const Wrapper = s.div`
  height: 100vh;
  width: 20vw;
  overflow-x: hidden;
  overflow-y: auto;
  position: fixed;
  top: 0;
  padding-top: ${NAV_HEIGHT};

  ${mediaMaxWidth(MD)} {
    position: relative;
    height: auto;
    overflow: visible;
    padding-top: 0;
    width: 100%;
  }
`

const Content = s.div`
  padding: 36px 17px 12px 17px;
  width: 100%;

  &::-webkit-scrollbar {
    display: none;
  }

  ${mediaMaxWidth(MD)} {
    position: relative;
    height: auto;
    overflow: visible;
    width: 100%;
    margin: 0;
    padding: 20px;
  }
`

const Input = s.input`
  border-width: 0;
  outline: none;
  color: ${CLUBS_GREY};
  width: 100%;
  font-size: 1em;
  padding: 8px 10px;
  background: ${HOVER_GRAY};
  border-radius: ${BORDER_RADIUS};

  &:hover,
  &:active,
  &:focus {
    background: ${FOCUS_GRAY};
  }
`

const SearchIcon = s.span`
  cursor: pointer;
  color: ${MEDIUM_GRAY};
  opacity: 0.5;
  padding-top: 8px;
  position: absolute;
  right: 20px;

  ${mediaMaxWidth(MD)} {
    right: 24px;
  }
`

class SearchBar extends React.Component {
  constructor(props) {
    super(props)
    this.state = {
      nameInput: '',
      sizeOptions: [
        { value: 1, label: 'less than 20 members' },
        { value: 2, label: '20 to 50 members' },
        { value: 3, label: '50 to 100 members' },
        { value: 4, label: 'more than 100' }
      ],
      tagOptions: props.tags.map((tag) => ({ value: tag.id, label: tag.name, count: tag.clubs })),
      applicationOptions: [
        { value: 1, label: 'Requires application' },
        { value: 2, label: 'Does not require application' },
        { value: 3, label: 'Currently accepting applications' }],
      selectedTags: props.selectedTags
    }
  }

  componentDidUpdate(prevProps, prevState) {
    if (prevState.nameInput !== this.state.nameInput) {
      clearTimeout(this.timeout)
      this.timeout = setTimeout(() => this.props.resetDisplay(this.state.nameInput, this.state.selectedTags), 200)
    }
  }

  render() {
    const { tagOptions, sizeOptions, applicationOptions, selectedTags } = this.state
    const { updateTag } = this.props
    return (
      <Wrapper>
        <Content>
          <div style={{ marginBottom: '30px' }}>
            <SearchIcon className="icon">
              {this.state.nameInput ? (
                <i
                  onClick={(e) => this.setState({ nameInput: '' })}
                  className="fas fa-times"
                />
              ) : (
                <i className="fas fa-search" />
              )}
            </SearchIcon>
            <Input
              type="text"
              name="search"
              placeholder="Search"
              aria-label="Search"
              value={this.state.nameInput}
              onChange={(e) => this.setState({ nameInput: e.target.value })}
            />
          </div>
          <DropdownFilter
            name="Type"
            options={tagOptions}
            selected={selectedTags.filter(tag => tag.name === 'Type')}
            updateTag={updateTag}
          />
          <DropdownFilter
            name="Size"
            options={sizeOptions}
            selected={selectedTags.filter(tag => tag.name === 'Size')}
            updateTag={updateTag}
          />
          <DropdownFilter
            name="Application"
            options={applicationOptions}
            selected={selectedTags.filter(tag => tag.name === 'Application')}
            updateTag={updateTag}
          />
        </Content>
      </Wrapper>
    )
  }
}

export default SearchBar
