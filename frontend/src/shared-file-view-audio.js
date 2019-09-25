import React from 'react';
import ReactDOM from 'react-dom';
import SharedFileViewPingan from './components/shared-file-view/pingan-shared-file-view';
import SharedFileViewTip from './components/shared-file-view/shared-file-view-tip';
import AudioPlayer from './components/audio-player';

import './css/audio-file-view.css';

const { rawPath, err } = window.shared.pageOptions;

class SharedFileViewAudio extends React.Component {
  render() {
    return <SharedFileViewPingan content={<FileContent />} />;
  }
}

class FileContent extends React.Component {
  render() {
    if (err) {
      return <SharedFileViewTip />;
    }

    const videoJsOptions = {
      autoplay: false,
      controls: true,
      preload: 'auto',
      sources: [{
        src: rawPath
      }]
    };
    return (
      <div className="shared-file-view-body d-flex">
        <div className="flex-1">
          <AudioPlayer { ...videoJsOptions } />
        </div>
      </div>
    );
  }
}

ReactDOM.render(
  <SharedFileViewAudio />,
  document.getElementById('wrapper')
);
