import React from 'react';
import PropTypes from 'prop-types';
import { Button, Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap';
import { gettext } from '../../utils/constants';
import { Utils } from '../../utils/utils';

const propTypes = {
  toggle: PropTypes.func.isRequired,
  item: PropTypes.object.isRequired,
};

class PinganShareLinkReceiverDialog extends React.Component {

  render() {
    let { item } = this.props;
    return (
      <Modal isOpen={true} toggle={this.props.toggle}>
        <ModalHeader toggle={this.props.toggle}>{gettext('接收人信息')}</ModalHeader>
        <ModalBody>
          <div>
            <ul>
              {
                item.sent_to.map((email, index) => {
                  return (<li className='ml-3' key={index}>{email}</li>)
                })
              }
            </ul>
          </div>
        </ModalBody>
        <ModalFooter>
          <Button color="secondary" onClick={this.props.toggle}>{gettext('Close')}</Button>
        </ModalFooter>
      </Modal>
    );
  }
}

PinganShareLinkReceiverDialog.propTypes = propTypes;

export default PinganShareLinkReceiverDialog;
