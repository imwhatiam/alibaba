import React from 'react';
import PropTypes from 'prop-types';
import { gettext } from '../../utils/constants';
import { Modal, ModalHeader, ModalBody, ModalFooter, Button } from 'reactstrap';

const propTypes = {
  currentResumableFile: PropTypes.object.isRequired,
  replaceRepetitionFolder: PropTypes.func.isRequired,
  uploadFolder: PropTypes.func.isRequired,
  cancelFolderUpload: PropTypes.func.isRequired,
};

class FolderUploadRemindDialog extends React.Component {


  toggle = (e) => {
    e.nativeEvent.stopImmediatePropagation();
    this.props.cancelFolderUpload();
  }

  replaceRepetitionFolder = (e) => {
    e.nativeEvent.stopImmediatePropagation();
    this.props.replaceRepetitionFolder();
  }

  uploadFolder = (e) => {
    e.nativeEvent.stopImmediatePropagation();
    this.props.uploadFolder();
  }

  render() {

    let title = gettext('Replace folder {foldername}?');
    title = title.replace('{foldername}', '<span class="a-simaulte">' + this.props.currentResumableFile.relativePath.split("/")[0] + '</span>');
    return (
      <Modal isOpen={true} toggle={this.toggle}>
        <ModalHeader toggle={this.toggle} ><div dangerouslySetInnerHTML={{__html: title}}></div></ModalHeader>
        <ModalBody>
          <p>{gettext('A folder with the same name already exists in this folder.')}</p>
          <p>{gettext('Replacing it will overwrite its content.')}</p>
        </ModalBody>
        <ModalFooter>
          <Button color="primary" onClick={this.replaceRepetitionFolder}>{gettext('Replace')}</Button>
          <Button color="primary" onClick={this.uploadFolder}>{gettext('Don\'t replace')}</Button>
          <Button color="secondary" onClick={this.toggle}>{gettext('Cancel')}</Button>
        </ModalFooter>
      </Modal>
    );
  }
}

FolderUploadRemindDialog.propTypes = propTypes;

export default FolderUploadRemindDialog;
