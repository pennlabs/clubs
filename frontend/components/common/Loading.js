import PropTypes from 'prop-types'
import { useEffect, useState } from 'react'
import s, { keyframes } from 'styled-components'

import { ALLBIRDS_GRAY, BLUE, BORDER } from '../../constants/colors'

const SIZE = '2.5rem'
const THICKNESS = '0.25rem'
const TIMER = '1.25s'

const LoadingWrapper = s.div`
  width: 100%;
  padding: calc(1rem + 5vh) 0;
  text-align: center;
  transition: opacity 0.5s ease;
  opacity: ${({ hide }) => (hide ? '0' : '1')};
`

const spin = keyframes`
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
`

const LoadingCircle = s.span`
  display: inline-block;
  width: ${SIZE};
  height: ${SIZE};
  border-radius: 50%;
  border-width: ${THICKNESS};
  border-style: solid;
  border-right-color: ${BORDER};
  border-left-color: ${BLUE};
  border-bottom-color: ${BLUE};
  border-top-color: ${BLUE};
  animation: ${spin} ${TIMER} infinite linear;
`

export const Loading = ({ title = 'Loading...', delay }) => {
  const [hidden, toggleHidden] = useState(true)

  useEffect(() => {
    if (hidden) {
      const timer = setTimeout(() => {
        toggleHidden(false)
      }, delay)
      return () => clearTimeout(timer)
    }
  })

  return (
    <LoadingWrapper hide={hidden}>
      <LoadingCircle />
      {title && <p style={{ color: ALLBIRDS_GRAY }}>{title}</p>}
    </LoadingWrapper>
  )
}

Loading.defaultProps = {
  title: null,
  delay: 200,
}

Loading.propTypes = {
  title: PropTypes.string,
  delay: PropTypes.number,
}
