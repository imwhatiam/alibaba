import React from 'react';
import PropTypes from 'prop-types';
import { gettext, maxUploadFileSize } from '../../utils/constants';

const propTypes = {
  file: PropTypes.object,
};

class ForbidUploadListItem extends React.Component {

  render() {
    let { file } = this.props;
    let isZHCN = window.app.config.lang === 'zh-cn';
    let msg = isZHCN ? 'Files with size of more than 10G can not be uploaded on web, please use client to synchronize the files.' : '单个文件超过10G不支持网页上传，请通过客户端同步上传。';
    return (
      <tr className="file-upload-item">
        <td className="upload-name">
          <div className="ellipsis">{file.name}</div>
        </td>

        <td colSpan={3} className="error">{msg}</td>
      </tr>
    );
  }
}

ForbidUploadListItem.propTypes = propTypes;

export default ForbidUploadListItem;
