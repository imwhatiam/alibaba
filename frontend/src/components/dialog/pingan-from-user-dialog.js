import React from 'react';
import PropTypes from 'prop-types';
import { Button, Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap';
import { gettext } from '../../utils/constants';

const propTypes = {
  toggle: PropTypes.func.isRequired,
  item: PropTypes.object.isRequired,
};

class PinganFromUserDialog extends React.Component {

  render() {
    let { item } = this.props;
    return (
      <Modal isOpen={true} toggle={this.props.toggle}>
        <ModalHeader toggle={this.props.toggle}>{gettext('发送人信息')}</ModalHeader>
        <ModalBody>
          <div>
            {'发送人：'}{item.from_user}<br/>
            {'发送人公司：'}{item.company}<br/>
            {'发送人部门：'}{item.department}
          </div>
        </ModalBody>
        <ModalFooter>
          <Button color="secondary" onClick={this.props.toggle}>{gettext('Close')}</Button>
        </ModalFooter>
      </Modal>
    );
  }
}

PinganFromUserDialog.propTypes = propTypes;

export default PinganFromUserDialog;
